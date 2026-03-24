#!/usr/bin/env python3
"""
CryptoEdge Pro — Test Runner
Uses built-in unittest. Run: python3 bot/tests/run_tests.py
"""
import sys, os, unittest

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hft_indicators import (
    ema, rsi, bollinger, vwap, stochastic, cci, macd_fast, atr, adx,
    price_action, find_sr_levels, near_level, htf_trend, higher_lows, lower_highs
)
from hft_trail import (
    calc_cost_floor, calc_lock_offset, build_trail_table,
    evaluate_trail, calc_active_sl, should_close, LEVEL_NAMES
)


# ═══════════════════════════════════════════════════════════════
#  INDICATOR TESTS
# ═══════════════════════════════════════════════════════════════

class TestEMA(unittest.TestCase):
    def test_basic(self):
        result = ema([1, 2, 3, 4, 5], 3)
        self.assertIsNotNone(result)
        self.assertGreater(result, 3.5)
        self.assertLess(result, 5.0)

    def test_insufficient_data(self):
        self.assertIsNone(ema([1, 2], 5))

    def test_constant_series(self):
        result = ema([5, 5, 5, 5, 5], 3)
        self.assertAlmostEqual(result, 5.0, places=2)


class TestRSI(unittest.TestCase):
    def test_uptrend_overbought(self):
        closes = list(range(1, 20))
        self.assertGreater(rsi(closes, 7), 70)

    def test_downtrend_oversold(self):
        closes = [20 - i for i in range(20)]
        self.assertLess(rsi(closes, 7), 30)

    def test_range(self):
        import random; random.seed(42)
        closes = [100 + random.uniform(-5, 5) for _ in range(50)]
        r = rsi(closes, 7)
        self.assertGreaterEqual(r, 0)
        self.assertLessEqual(r, 100)

    def test_insufficient(self):
        self.assertEqual(rsi([1, 2, 3], 7), 50.0)


class TestBollinger(unittest.TestCase):
    def test_basic(self):
        closes = [100 + i * 0.1 for i in range(20)]
        result = bollinger(closes, 14, 2.0)
        self.assertIsNotNone(result)
        upper, mid, lower, pct_b, bw = result
        self.assertGreater(upper, mid)
        self.assertGreater(mid, lower)

    def test_insufficient(self):
        self.assertIsNone(bollinger([1, 2, 3], 14))

    def test_constant_returns_none(self):
        self.assertIsNone(bollinger([100] * 20, 14, 2.0))


class TestVWAP(unittest.TestCase):
    def test_basic(self):
        closes = [100, 101, 102, 103, 104]
        volumes = [1000, 2000, 1500, 3000, 2500]
        result = vwap(closes, volumes)
        self.assertIsNotNone(result)
        self.assertGreater(result, 100)

    def test_zero_volume(self):
        self.assertIsNone(vwap([100] * 5, [0] * 5))


class TestATRandADX(unittest.TestCase):
    def test_atr_positive(self):
        result = atr([101, 102, 103], [99, 100, 101], [100, 101, 102], 2)
        self.assertGreater(result, 0)

    def test_adx_trending(self):
        closes = [100 + i * 2 for i in range(20)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        self.assertGreater(adx(highs, lows, closes), 10)


class TestHTFTrend(unittest.TestCase):
    def test_uptrend(self):
        closes = [100 + i * 0.5 for i in range(80)]
        d, _ = htf_trend(closes)
        self.assertEqual(d, 'up')

    def test_downtrend(self):
        closes = [200 - i * 0.5 for i in range(80)]
        d, _ = htf_trend(closes)
        self.assertEqual(d, 'down')

    def test_neutral(self):
        d, _ = htf_trend([100.0] * 80)
        self.assertEqual(d, 'neutral')

    def test_insufficient(self):
        d, _ = htf_trend([100] * 10)
        self.assertEqual(d, 'neutral')


class TestSRLevels(unittest.TestCase):
    def test_near_level_found(self):
        self.assertEqual(near_level(100.0, [99.9, 105.0], 0.15), 99.9)

    def test_near_level_not_found(self):
        self.assertIsNone(near_level(100.0, [95.0, 110.0], 0.15))


class TestPriceAction(unittest.TestCase):
    def test_bullish_engulfing(self):
        result = price_action([102, 99], [100, 103], [103, 104], [99, 98])
        self.assertEqual(result, 'BUY')

    def test_bearish_engulfing(self):
        result = price_action([100, 103], [102, 99], [103, 104], [99, 98])
        self.assertEqual(result, 'SELL')


# ═══════════════════════════════════════════════════════════════
#  TRAIL STOP TESTS
# ═══════════════════════════════════════════════════════════════

class TestCostFloor(unittest.TestCase):
    def test_default(self):
        floor = calc_cost_floor(0.0005, 0.03, 0.02)
        self.assertAlmostEqual(floor, 0.15, places=2)


class TestTrailTable(unittest.TestCase):
    def test_six_levels(self):
        table = build_trail_table()
        self.assertEqual(len(table), 6)

    def test_sorted_desc(self):
        table = build_trail_table()
        levels = [t[0] for t in table]
        self.assertEqual(levels, [6, 5, 4, 3, 2, 1])

    def test_triggers_ascending(self):
        table = build_trail_table()
        triggers = {t[0]: t[1] for t in table}
        self.assertLess(triggers[1], triggers[2])
        self.assertLess(triggers[2], triggers[3])
        self.assertLess(triggers[3], triggers[4])

    def test_locks_positive(self):
        for lv, trigger, lock in build_trail_table():
            self.assertGreater(lock, 0, f"L{lv} lock should be > 0")

    def test_locks_less_than_trigger(self):
        for lv, trigger, lock in build_trail_table():
            self.assertLessEqual(lock, trigger, f"L{lv} lock {lock} > trigger {trigger}")


class TestEvaluateTrail(unittest.TestCase):
    def setUp(self):
        self.table = build_trail_table()
        self.dyn_gaps = {4: 0.30, 5: 0.40, 6: 0.60}

    def test_no_trail_below_l1(self):
        lv, tsl, changed = evaluate_trail(0.30, 100.0, 'BUY', 0, None, self.table)
        self.assertEqual(lv, 0)
        self.assertIsNone(tsl)
        self.assertFalse(changed)

    def test_l1_buy(self):
        lv, tsl, changed = evaluate_trail(0.55, 100.0, 'BUY', 0, None, self.table)
        self.assertEqual(lv, 1)
        self.assertGreater(tsl, 100.0)
        self.assertTrue(changed)

    def test_l1_sell(self):
        lv, tsl, changed = evaluate_trail(0.55, 100.0, 'SELL', 0, None, self.table)
        self.assertEqual(lv, 1)
        self.assertLess(tsl, 100.0)
        self.assertTrue(changed)

    def test_l3_activation(self):
        lv, tsl, changed = evaluate_trail(1.05, 100.0, 'BUY', 0, None, self.table)
        self.assertGreaterEqual(lv, 3)
        self.assertGreater(tsl, 100.0)

    def test_l6_max(self):
        lv, tsl, _ = evaluate_trail(4.20, 100.0, 'BUY', 0, None, self.table)
        self.assertEqual(lv, 6)
        self.assertGreater(tsl, 103.0)

    def test_trail_never_recedes_buy(self):
        _, tsl_high, _ = evaluate_trail(0.75, 100.0, 'BUY', 0, None, self.table)
        _, tsl_after, _ = evaluate_trail(0.55, 100.0, 'BUY', 2, tsl_high, self.table)
        if tsl_after is not None:
            self.assertGreaterEqual(tsl_after, tsl_high)

    def test_trail_never_recedes_sell(self):
        _, tsl_high, _ = evaluate_trail(0.75, 100.0, 'SELL', 0, None, self.table)
        _, tsl_after, _ = evaluate_trail(0.55, 100.0, 'SELL', 2, tsl_high, self.table)
        if tsl_after is not None:
            self.assertLessEqual(tsl_after, tsl_high)

    def test_buy_trail_always_above_entry(self):
        for pnl in [0.55, 0.75, 1.05, 1.55, 2.60, 4.20]:
            _, tsl, _ = evaluate_trail(pnl, 100.0, 'BUY', 0, None, self.table)
            if tsl is not None:
                self.assertGreater(tsl, 100.0, f"BUY L pnl={pnl}%")

    def test_sell_trail_always_below_entry(self):
        for pnl in [0.55, 0.75, 1.05, 1.55, 2.60, 4.20]:
            _, tsl, _ = evaluate_trail(pnl, 100.0, 'SELL', 0, None, self.table)
            if tsl is not None:
                self.assertLess(tsl, 100.0, f"SELL L pnl={pnl}%")

    def test_dynamic_l4(self):
        lv, tsl, _ = evaluate_trail(2.00, 100.0, 'BUY', 4, 101.20, self.table, self.dyn_gaps)
        self.assertGreater(tsl, 101.20)


class TestActiveSL(unittest.TestCase):
    def test_buy_trail_better(self):
        self.assertEqual(calc_active_sl('BUY', 99.0, 101.0), 101.0)

    def test_sell_trail_better(self):
        self.assertEqual(calc_active_sl('SELL', 105.0, 99.0), 99.0)

    def test_no_trail(self):
        self.assertEqual(calc_active_sl('BUY', 99.0, None), 99.0)


class TestShouldClose(unittest.TestCase):
    def test_buy_sl_hit(self):
        result = should_close('BUY', 98.0, 99.0, 110.0, True, -2.0, 100, 7200)
        self.assertEqual(result, 'trail_hit')

    def test_sell_sl_hit(self):
        result = should_close('SELL', 102.0, 101.0, 90.0, True, -2.0, 100, 7200)
        self.assertEqual(result, 'trail_hit')

    def test_stay_open(self):
        self.assertIsNone(should_close('BUY', 101.0, 99.0, 110.0, True, 1.0, 100, 7200))

    def test_time_exit_loss(self):
        result = should_close('BUY', 99.5, 99.0, 110.0, True, -0.5, 25000, 7200)
        self.assertIn('Time-exit', result)


# ═══════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Load all test classes
    for cls in [
        TestEMA, TestRSI, TestBollinger, TestVWAP, TestATRandADX,
        TestHTFTrend, TestSRLevels, TestPriceAction,
        TestCostFloor, TestTrailTable, TestEvaluateTrail,
        TestActiveSL, TestShouldClose,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print(f"\n{'='*60}")
    print(f"  RESULTADO: {result.testsRun} testes | "
          f"{'✅ TODOS PASSARAM' if result.wasSuccessful() else f'❌ {len(result.failures)} falhas'}")
    print(f"{'='*60}")

    sys.exit(0 if result.wasSuccessful() else 1)
