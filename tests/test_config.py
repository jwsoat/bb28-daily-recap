from datetime import date

import pytest

from bb28_recap.config import (
    REQUIRED_ENV_VARS,
    MissingEnvVarError,
    compute_day_number,
    load_env_config,
)


def test_compute_day_number_is_1_on_start_date():
    assert compute_day_number(date(2026, 7, 9), "2026-07-09") == 1


def test_compute_day_number_increments_daily():
    assert compute_day_number(date(2026, 7, 12), "2026-07-09") == 4


def test_compute_day_number_is_0_before_start():
    assert compute_day_number(date(2026, 7, 1), "2026-07-09") == 0


def test_load_env_config_returns_all_required_values():
    env = {name: f"value-{name}" for name in REQUIRED_ENV_VARS}
    config = load_env_config(env)
    assert config == env


def test_load_env_config_raises_on_missing_vars():
    env = {name: f"value-{name}" for name in REQUIRED_ENV_VARS if name != "ANTHROPIC_API_KEY"}
    with pytest.raises(MissingEnvVarError, match="ANTHROPIC_API_KEY"):
        load_env_config(env)
