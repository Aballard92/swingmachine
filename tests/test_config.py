from __future__ import annotations

from pathlib import Path

from swingmachine.config import StrategyRuntimeConfig, load_strategy_config
from swingmachine.enums import OrderType, RegimeState

CONFIG_PATH = Path("swing_trading_bot_config_template_v2.yaml")


def test_load_strategy_config() -> None:
    config = load_strategy_config(CONFIG_PATH)

    assert isinstance(config, StrategyRuntimeConfig)
    assert config.strategy.id == "RF_TPC_V2"
    assert config.strategy.version == "2.1.0"
    assert config.entry.order_type is OrderType.STOP_LIMIT
    assert config.regime_action(RegimeState.CAUTION).size_multiplier == 0.5
    assert config.events.min_regular_closes_before_earnings_for_new_entry == 5
    assert config.benchmark_relative_features.compute is True
    assert config.benchmark_relative_features.influence_strategy_behavior is False
    assert config.benchmark_relative_features.relative_strength_windows == (20, 50, 100, 126)
    assert config.benchmark_relative_features.acceleration_pairs[0].short_window == 20
    assert config.benchmark_relative_features.acceleration_pairs[0].long_window == 100


def test_config_hash_is_stable_for_same_file() -> None:
    first = load_strategy_config(CONFIG_PATH)
    second = load_strategy_config(CONFIG_PATH)

    assert first.config_hash() == second.config_hash()
