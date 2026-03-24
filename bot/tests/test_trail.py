"""
Tests for CryptoEdge Pro — Trail Stop Logic
Run: python -m pytest bot/tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hft_trail import (
    calc_cost_floor, calc_lock_offset, build_trail_table,
    evaluate_trail, calc_active_sl, should_close, LEVEL_NAMES
)


class TestCostFloor:
    def test_default(self):
        floor = calc_cost_floor(0.0005, 0.03, 0.02)
        assert abs(floor - 0.15) < 0.01  # 0.10 + 0.03 + 0.02

    def test_zero_fees(self):
        floor = calc_cost_floor(0, 0, 0)
        assert floor == 0


class TestLockOffset:
    def test_normal(self):
        # trigger=0.80, gap=0.30, floor=0.15
        k = calc_lock_offset(0.80, 0.30, 0.15)
        assert abs(k - 0.50) < 0.01

    def test_floor_applies(self):
        # trigger=0.30, gap=0.30 → would be 0, but floor=0.15
        k = calc_lock_offset(0.30, 0.30, 0.15)
        assert abs(k - 0.15) < 0.01


class TestBuildTrailTable:
    def test_default(self):
        table = build_trail_table()
        assert len(table) == 6
        # Should be sorted by level DESC
        levels = [t[0] for t in table]
        assert levels == [6, 5, 4, 3, 2, 1]

    def test_triggers_ascending(self):
        table = build_trail_table()
        # Triggers should increase with level
        triggers = {t[0]: t[1] for t in table}
        assert triggers[1] < triggers[2] < triggers[3] < triggers[4] < triggers[5] < triggers[6]

    def test_locks_ascending(self):
        table = build_trail_table()
        locks = {t[0]: t[2] for t in table}
        # Lock offsets should increase with level
        assert locks[1] <= locks[2] <= locks[3] <= locks[4] <= locks[5] <= locks[6]

    def test_lock_always_positive(self):
        table = build_trail_table()
        for lv, trigger, lock in table:
            assert lock > 0, f"L{lv} lock offset should be > 0, got {lock}"

    def test_lock_less_than_trigger(self):
        table = build_trail_table()
        for lv, trigger, lock in table:
            assert lock <= trigger, f"L{lv} lock {lock} > trigger {trigger}"


class TestEvaluateTrail:
    def setup_method(self):
        self.table = build_trail_table()
        self.dyn_gaps = {4: 0.35, 5: 0.50, 6: 0.70}

    def test_no_trail_below_l1(self):
        """PnL below L1 trigger → no trail activation."""
        new_lv, new_tsl, changed = evaluate_trail(
            pnl_pct=0.10, entry=100.0, side='BUY',
            cur_level=0, cur_trail_sl=None,
            trail_table=self.table
        )
        assert new_lv == 0
        assert new_tsl is None
        assert changed is False

    def test_l1_activation_buy(self):
        """BUY: PnL >= 0.30% → L1 activates."""
        new_lv, new_tsl, changed = evaluate_trail(
            pnl_pct=0.35, entry=100.0, side='BUY',
            cur_level=0, cur_trail_sl=None,
            trail_table=self.table
        )
        assert new_lv == 1
        assert new_tsl is not None
        assert new_tsl > 100.0  # BUY: trail SL above entry
        assert changed is True

    def test_l1_activation_sell(self):
        """SELL: PnL >= 0.30% → L1 activates."""
        new_lv, new_tsl, changed = evaluate_trail(
            pnl_pct=0.35, entry=100.0, side='SELL',
            cur_level=0, cur_trail_sl=None,
            trail_table=self.table
        )
        assert new_lv == 1
        assert new_tsl is not None
        assert new_tsl < 100.0  # SELL: trail SL below entry
        assert changed is True

    def test_l3_activation(self):
        """PnL >= 0.80% → L3 activates."""
        new_lv, new_tsl, changed = evaluate_trail(
            pnl_pct=0.85, entry=100.0, side='BUY',
            cur_level=0, cur_trail_sl=None,
            trail_table=self.table
        )
        assert new_lv == 3
        assert changed is True
        assert new_tsl > 100.0

    def test_trail_never_recedes_buy(self):
        """BUY: trail SL should never go down."""
        _, tsl_l2, _ = evaluate_trail(
            pnl_pct=0.55, entry=100.0, side='BUY',
            cur_level=0, cur_trail_sl=None,
            trail_table=self.table
        )
        # Now if PnL drops back but still above L1
        new_lv, new_tsl, _ = evaluate_trail(
            pnl_pct=0.35, entry=100.0, side='BUY',
            cur_level=2, cur_trail_sl=tsl_l2,
            trail_table=self.table
        )
        # Trail should NOT drop below L2 level
        assert new_tsl >= tsl_l2 or new_tsl is None

    def test_trail_never_recedes_sell(self):
        """SELL: trail SL should never go up."""
        _, tsl_l2, _ = evaluate_trail(
            pnl_pct=0.55, entry=100.0, side='SELL',
            cur_level=0, cur_trail_sl=None,
            trail_table=self.table
        )
        new_lv, new_tsl, _ = evaluate_trail(
            pnl_pct=0.35, entry=100.0, side='SELL',
            cur_level=2, cur_trail_sl=tsl_l2,
            trail_table=self.table
        )
        assert new_tsl <= tsl_l2 or new_tsl is None

    def test_dynamic_trail_l4(self):
        """L4+ should use dynamic trailing."""
        new_lv, new_tsl, _ = evaluate_trail(
            pnl_pct=1.50, entry=100.0, side='BUY',
            cur_level=4, cur_trail_sl=100.85,
            trail_table=self.table, dyn_gaps=self.dyn_gaps
        )
        # Dynamic should set trail higher than static L4
        assert new_tsl > 100.85

    def test_l6_max_protection(self):
        """L6 at 3%+ should lock significant profit."""
        new_lv, new_tsl, changed = evaluate_trail(
            pnl_pct=3.50, entry=100.0, side='BUY',
            cur_level=0, cur_trail_sl=None,
            trail_table=self.table
        )
        assert new_lv == 6
        assert new_tsl > 102.0  # should lock at least 2%

    def test_buy_trail_sl_positive(self):
        """BUY trail SL should always be above entry at L1+."""
        for pnl in [0.35, 0.55, 0.85, 1.25, 2.10, 3.10]:
            _, tsl, _ = evaluate_trail(
                pnl_pct=pnl, entry=100.0, side='BUY',
                cur_level=0, cur_trail_sl=None,
                trail_table=self.table
            )
            if tsl is not None:
                assert tsl > 100.0, f"BUY trail SL at pnl={pnl}% should be > entry"

    def test_sell_trail_sl_negative(self):
        """SELL trail SL should always be below entry at L1+."""
        for pnl in [0.35, 0.55, 0.85, 1.25, 2.10, 3.10]:
            _, tsl, _ = evaluate_trail(
                pnl_pct=pnl, entry=100.0, side='SELL',
                cur_level=0, cur_trail_sl=None,
                trail_table=self.table
            )
            if tsl is not None:
                assert tsl < 100.0, f"SELL trail SL at pnl={pnl}% should be < entry"


class TestActiveSL:
    def test_buy_trail_better(self):
        # Trail SL at 101, orig SL at 99 → use 101
        result = calc_active_sl('BUY', 99.0, 101.0)
        assert result == 101.0

    def test_buy_orig_better(self):
        result = calc_active_sl('BUY', 101.0, 99.0)
        assert result == 101.0

    def test_sell_trail_better(self):
        result = calc_active_sl('SELL', 105.0, 99.0)
        assert result == 99.0

    def test_sell_orig_better(self):
        result = calc_active_sl('SELL', 99.0, 105.0)
        assert result == 99.0

    def test_no_trail(self):
        assert calc_active_sl('BUY', 99.0, None) == 99.0
        assert calc_active_sl('SELL', 101.0, None) == 101.0


class TestShouldClose:
    def test_buy_sl_hit(self):
        result = should_close('BUY', 98.0, 99.0, 110.0, True, -2.0, 100, 7200)
        assert result == 'trail_hit'

    def test_sell_sl_hit(self):
        result = should_close('SELL', 102.0, 101.0, 90.0, True, -2.0, 100, 7200)
        assert result == 'trail_hit'

    def test_buy_above_sl(self):
        result = should_close('BUY', 101.0, 99.0, 110.0, True, 1.0, 100, 7200)
        assert result is None

    def test_sell_below_sl(self):
        result = should_close('SELL', 99.0, 101.0, 90.0, True, 1.0, 100, 7200)
        assert result is None

    def test_time_exit_loss(self):
        result = should_close('BUY', 99.5, 99.0, 110.0, True, -0.5, 25000, 7200)
        assert 'Time-exit' in result

    def test_time_exit_profit_stays(self):
        result = should_close('BUY', 101.0, 99.0, 110.0, True, 1.0, 25000, 7200)
        assert result is None  # profitable, don't time-exit


class TestLevelNames:
    def test_all_levels_named(self):
        for i in range(1, 7):
            assert i in LEVEL_NAMES


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
