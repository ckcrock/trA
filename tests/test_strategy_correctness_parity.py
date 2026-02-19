from src.engine.lifecycle import StrategyLifecycleManager
from src.strategies.base_strategy import BaseStrategy


class _TestStrategy(BaseStrategy):
    def on_bar(self, bar):
        super().on_bar(bar)


def test_signal_schema_contains_trace_fields():
    s = _TestStrategy({"name": "trace_test"})
    s.generate_signal("BUY", 100.5, "entry")
    signal = s.signals[-1]
    assert signal["signal_id"] == "trace_test-1"
    assert signal["schema_version"] == "v1"
    assert signal["strategy"] == "trace_test"
    assert signal["price"] == 100.5


def test_signal_type_validation():
    s = _TestStrategy({"name": "signal_type_test"})
    try:
        s.generate_signal("INVALID", 100.0, "bad")
        assert False, "Expected ValueError for invalid signal type"
    except ValueError:
        assert True


def test_short_position_weighted_average_entry():
    s = _TestStrategy({"name": "short_avg_test"})
    s.update_position("SELL", 10, 100.0)  # short 10 @100
    s.update_position("SELL", 10, 90.0)   # add short 10 @90 => avg 95
    assert s.position == -20
    assert round(s.entry_price, 2) == 95.0


def test_lifecycle_signal_count_tracks_strategy_signals():
    s = _TestStrategy({"name": "life_test"})
    lm = StrategyLifecycleManager()
    assert lm.register("life_test", s)
    s.generate_signal("BUY", 100.0, "x")
    s.generate_signal("HOLD", 101.0, "")
    status = lm.get_status("life_test")
    assert status["signal_count"] == 2
