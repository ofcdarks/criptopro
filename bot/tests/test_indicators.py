"""
Tests for CryptoEdge Pro — Technical Indicators
Run: python -m pytest bot/tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hft_indicators import (
    ema, rsi, bollinger, vwap, stochastic, cci, macd_fast, atr, adx,
    price_action, find_sr_levels, near_level, htf_trend, higher_lows, lower_highs
)


class TestEMA:
    def test_basic(self):
        result = ema([1, 2, 3, 4, 5], 3)
        assert result is not None
        assert 3.5 < result < 5.0

    def test_insufficient_data(self):
        assert ema([1, 2], 5) is None

    def test_single_value(self):
        assert ema([10], 1) == 10

    def test_constant_series(self):
        result = ema([5, 5, 5, 5, 5], 3)
        assert abs(result - 5.0) < 0.001


class TestRSI:
    def test_uptrend(self):
        closes = [i for i in range(1, 20)]  # steady uptrend
        result = rsi(closes, 7)
        assert result > 70  # should be overbought

    def test_downtrend(self):
        closes = [20 - i for i in range(20)]  # steady downtrend
        result = rsi(closes, 7)
        assert result < 30  # should be oversold

    def test_flat_market(self):
        closes = [100] * 20
        result = rsi(closes, 7)
        assert result == 100.0  # no losses = RSI 100

    def test_insufficient_data(self):
        result = rsi([1, 2, 3], 7)
        assert result == 50.0  # default

    def test_range(self):
        import random
        random.seed(42)
        closes = [100 + random.uniform(-5, 5) for _ in range(50)]
        result = rsi(closes, 7)
        assert 0 <= result <= 100


class TestBollinger:
    def test_basic(self):
        closes = [100 + i * 0.1 for i in range(20)]
        result = bollinger(closes, 14, 2.0)
        assert result is not None
        upper, mid, lower, pct_b, bw = result
        assert upper > mid > lower
        assert 0 <= pct_b <= 1.0
        assert bw > 0

    def test_insufficient_data(self):
        assert bollinger([1, 2, 3], 14) is None

    def test_constant_returns_none(self):
        result = bollinger([100] * 20, 14, 2.0)
        assert result is None  # std=0

    def test_price_at_upper_band(self):
        # Price trending up strongly
        closes = [100 + i * 2 for i in range(20)]
        result = bollinger(closes, 14, 2.0)
        assert result is not None
        _, _, _, pct_b, _ = result
        assert pct_b > 0.7  # near upper band


class TestVWAP:
    def test_basic(self):
        closes = [100, 101, 102, 103, 104]
        volumes = [1000, 2000, 1500, 3000, 2500]
        result = vwap(closes, volumes)
        assert result is not None
        assert 100 < result < 105

    def test_insufficient_data(self):
        assert vwap([1], [1]) is None

    def test_zero_volume(self):
        assert vwap([100] * 5, [0] * 5) is None


class TestStochastic:
    def test_basic(self):
        closes = list(range(10, 30))
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        k, d = stochastic(closes, highs, lows)
        assert 0 <= k <= 100
        assert 0 <= d <= 100

    def test_overbought(self):
        # Price at highs
        closes = list(range(10, 30))
        highs = [c + 0.1 for c in closes]
        lows = [c - 5 for c in closes]
        k, d = stochastic(closes, highs, lows)
        assert k > 70


class TestCCI:
    def test_basic(self):
        closes = [100 + i for i in range(20)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        result = cci(closes, highs, lows)
        assert isinstance(result, float)

    def test_insufficient(self):
        assert cci([1], [2], [0]) == 0.0


class TestMACDFast:
    def test_basic(self):
        closes = list(range(100, 120))
        ml, sl, hist = macd_fast(closes)
        assert isinstance(ml, (int, float))
        assert isinstance(hist, (int, float))

    def test_uptrend_positive(self):
        closes = [100 + i * 0.5 for i in range(20)]
        ml, _, hist = macd_fast(closes)
        assert ml > 0  # fast > slow in uptrend


class TestATR:
    def test_basic(self):
        highs = [101, 102, 103, 104, 105]
        lows = [99, 100, 101, 102, 103]
        closes = [100, 101, 102, 103, 104]
        result = atr(highs, lows, closes, 3)
        assert result > 0

    def test_flat_market(self):
        result = atr([100] * 5, [100] * 5, [100] * 5, 3)
        assert result == 0


class TestADX:
    def test_trending(self):
        # Strong uptrend
        closes = [100 + i * 2 for i in range(20)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        result = adx(highs, lows, closes)
        assert result > 15  # should show direction

    def test_insufficient(self):
        assert adx([1], [1], [1]) == 0


class TestPriceAction:
    def test_bullish_engulfing(self):
        opens = [102, 99]    # prev red, curr starts low
        closes = [100, 103]   # prev close < open, curr close > open (engulfing)
        highs = [103, 104]
        lows = [99, 98]
        result = price_action(opens, closes, highs, lows)
        assert result == 'BUY'

    def test_bearish_engulfing(self):
        opens = [100, 103]
        closes = [102, 99]
        highs = [103, 104]
        lows = [99, 98]
        result = price_action(opens, closes, highs, lows)
        assert result == 'SELL'

    def test_no_pattern(self):
        opens = [100, 100.5]
        closes = [100.5, 101]
        highs = [101, 101.5]
        lows = [99.5, 100]
        result = price_action(opens, closes, highs, lows)
        assert result is None

    def test_insufficient(self):
        assert price_action([100], [101], [102], [99]) is None


class TestSRLevels:
    def test_find_levels(self):
        # Create zigzag pattern
        data = []
        for i in range(50):
            if i % 10 < 5:
                data.append(100 + i % 10)
            else:
                data.append(105 - i % 10)
        supports, resistances = find_sr_levels(data, data)
        # Should find at least some levels
        assert isinstance(supports, list)
        assert isinstance(resistances, list)

    def test_insufficient(self):
        s, r = find_sr_levels([1, 2, 3], [1, 2, 3])
        assert s == [] and r == []


class TestNearLevel:
    def test_near(self):
        result = near_level(100.0, [99.9, 105.0], 0.15)
        assert result == 99.9

    def test_not_near(self):
        result = near_level(100.0, [95.0, 110.0], 0.15)
        assert result is None

    def test_empty(self):
        assert near_level(100.0, [], 0.15) is None


class TestHTFTrend:
    def test_uptrend(self):
        closes = [100 + i * 0.5 for i in range(80)]
        direction, force = htf_trend(closes)
        assert direction == 'up'
        assert force > 0

    def test_downtrend(self):
        closes = [200 - i * 0.5 for i in range(80)]
        direction, force = htf_trend(closes)
        assert direction == 'down'
        assert force < 0

    def test_neutral(self):
        # Flat market
        closes = [100.0] * 80
        direction, _ = htf_trend(closes)
        assert direction == 'neutral'

    def test_insufficient(self):
        direction, _ = htf_trend([100] * 10)
        assert direction == 'neutral'


class TestStructure:
    def test_higher_lows(self):
        # Create pattern with ascending lows
        lows = [10, 9, 8, 9.5, 10, 9, 8.5, 10, 11, 9.5, 9, 10.5, 11, 10, 9.5, 11, 12, 10.5, 10, 11.5, 12, 11, 10.5, 12, 13]
        result = higher_lows(lows)
        assert isinstance(result, bool)

    def test_lower_highs(self):
        highs = [20, 19, 21, 18, 20, 17, 19, 16, 18, 15, 17, 14, 16, 13, 15, 12, 14, 11, 13, 10, 12]
        result = lower_highs(highs)
        assert isinstance(result, bool)

    def test_insufficient(self):
        assert higher_lows([1, 2]) is False
        assert lower_highs([1, 2]) is False


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
