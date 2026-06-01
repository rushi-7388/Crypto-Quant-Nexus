"""Event-driven pipeline primitives for async inference."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class InferenceEvent:
    trace_id: str
    symbol: str
    use_live: bool
    window: int


class LocalEventBus:
    """Simple in-memory async bus, useful for local/dev fallback."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    async def publish(self, event: InferenceEvent) -> None:
        await self._queue.put(json.dumps(event.__dict__))

    async def consume(self) -> dict[str, Any]:
        raw = await self._queue.get()
        return json.loads(raw)


async def kafka_publish(
    *,
    topic: str,
    bootstrap_servers: str,
    payload: dict[str, Any],
) -> None:
    try:
        from aiokafka import AIOKafkaProducer
    except Exception as exc:
        raise RuntimeError("aiokafka is required for kafka_publish") from exc
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
    await producer.start()
    try:
        await producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))
    finally:
        await producer.stop()
