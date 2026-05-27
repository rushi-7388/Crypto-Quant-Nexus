"""Market microstructure helpers."""

from quant_core.orderbook import avellaneda_stoikov_spread, order_flow_imbalance, simulate_lob


def test_lob_has_both_sides():
    lob = simulate_lob(100_000.0, levels=5, seed=1)
    assert set(lob["side"]) == {"bid", "ask"}
    assert len(lob) == 10


def test_as_spread_inventory_skews_reservation():
    mid, inv_low, inv_high = 50_000.0, 0.0, 50.0
    bid_low, ask_low = avellaneda_stoikov_spread(mid, inv_low, gamma=0.1, sigma=0.02)
    bid_high, ask_high = avellaneda_stoikov_spread(mid, inv_high, gamma=0.1, sigma=0.02)
    assert bid_low != bid_high or ask_low != ask_high


def test_ofi_positive_on_bid_increase():
    ofi = order_flow_imbalance(bid_vol=10, ask_vol=5, prev_bid=5, prev_ask=5)
    assert ofi > 0
