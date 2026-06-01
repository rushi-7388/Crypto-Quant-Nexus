"""Async inference worker for event-driven alpha scoring."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quant_core.audit import append_decision_audit
from quant_core.events_store import RESULT_LOG, append_event
from quant_core.logging_config import configure_logging
from quant_core.observability import current_trace_id, start_trace
from quant_core.research.alpha_fusion import composite_alpha

configure_logging(service_name="inference-worker")
logger = logging.getLogger(__name__)


async def run_kafka_worker() -> None:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("KAFKA_TOPIC_INFERENCE_REQUEST", "inference.requests")
    result_topic = os.getenv("KAFKA_TOPIC_INFERENCE_RESULT", "inference.results")
    group = os.getenv("KAFKA_GROUP_ID", "quant-inference-workers")
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group,
        enable_auto_commit=True,
        auto_offset_reset="latest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    await consumer.start()
    await producer.start()
    logger.info("worker_started topic=%s bootstrap=%s", topic, bootstrap)
    try:
        async for msg in consumer:
            started = perf_counter()
            payload = json.loads(msg.value.decode("utf-8"))
            trace_id = payload.get("trace_id") or current_trace_id()
            start_trace(trace_id)
            symbol = payload.get("symbol", "BTC/USDT")
            use_live = bool(payload.get("use_live", True))
            window = int(payload.get("window", 500))
            alpha = composite_alpha(symbol=symbol, use_live=use_live, window=window)
            append_decision_audit(
                trace_id=trace_id,
                symbol=symbol,
                model_version="alpha_fusion_v1",
                dataset_version="market_feed_v1",
                decision={
                    "recommendation": alpha["recommendation"],
                    "score": alpha["composite_score"],
                },
                rationale=alpha["components"],
            )
            processed_ms = (perf_counter() - started) * 1000
            result_event = {
                "trace_id": trace_id,
                "symbol": symbol,
                "score": alpha["composite_score"],
                "recommendation": alpha["recommendation"],
                "processed_ms": round(processed_ms, 2),
            }
            await producer.send_and_wait(
                result_topic,
                json.dumps(result_event).encode("utf-8"),
            )
            append_event(RESULT_LOG, result_event)
            logger.info(
                "inference_scored trace_id=%s symbol=%s score=%.4f",
                trace_id,
                symbol,
                alpha["composite_score"],
            )
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(run_kafka_worker())
