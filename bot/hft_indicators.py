"""
CryptoEdge Pro — Technical Indicators Module
Pure functions for technical analysis. No side effects, no state.
Each function takes data arrays and returns calculated values.
"""

import math
from typing import List, Tuple, Optional


def ema(values: list, period: int) -> Optional[float]:
    """Exponential Moving Average."""
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


def rsi(closes: list, period: int = 7) -> float:
    """Relative Strength Index."""
    c = list(closes)
    if len(c) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(c)):
        d = c[i] - c[i - 1]
        gains.append(d if d > 0 else 0)
        losses.append(-d if d < 0 else 0)
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return 100 - (100 / (1 + rs))


def bollinger(closes: list, period: int = 14, num_std: float = 2.0) -> Optional[Tuple[float, float, float, float, float]]:
    """Bollinger Bands. Returns (upper, middle, lower, pct_b, bandwidth)."""
    c = list(closes)
    if len(c) < period:
        return None
    window = c[-period:]
    mid = sum(window) / period
    std = (sum((x - mid) ** 2 for x in window) / period) ** 0.5
    if std == 0:
        return None
    upper = mid + num_std * std
    lower = mid - num_std * std
    bw_range = upper - lower
    pct_b = (c[-1] - lower) / bw_range if bw_range > 0 else 0.5
    bandwidth = bw_range / mid if mid > 0 else 0
    return upper, mid, lower, pct_b, bandwidth


def vwap(closes: list, volumes: list, period: int = 20) -> Optional[float]:
    """Volume Weighted Average Price."""
    c = list(closes)[-period:]
    v = list(volumes)[-period:]
    if len(c) < 5 or len(v) < 5:
        return None
    tv = sum(v)
    if tv == 0:
        return None
    return sum(c[i] * v[i] for i in range(len(c))) / tv


def stochastic(closes: list, highs: list, lows: list,
               k_period: int = 9, d_period: int = 3) -> Tuple[float, float]:
    """Stochastic Oscillator. Returns (%K, %D)."""
    c = list(closes)
    h = list(highs)
    l = list(lows)
    if len(c) < k_period:
        return 50.0, 50.0
    k_values = []
    for i in range(max(0, len(c) - k_period - d_period), len(c)):
        start = max(0, i - k_period + 1)
        hh = max(h[start:i + 1])
        ll = min(l[start:i + 1])
        if hh == ll:
            k_values.append(50.0)
        else:
            k_values.append((c[i] - ll) / (hh - ll) * 100)
    stk = k_values[-1] if k_values else 50.0
    std = sum(k_values[-d_period:]) / min(d_period, len(k_values)) if k_values else 50.0
    return stk, std


def cci(closes: list, highs: list, lows: list, period: int = 14) -> float:
    """Commodity Channel Index."""
    c = list(closes)
    h = list(highs)
    l = list(lows)
    if len(c) < period:
        return 0.0
    tp = [(h[i] + l[i] + c[i]) / 3 for i in range(len(c))]
    tp_w = tp[-period:]
    mean = sum(tp_w) / period
    md = sum(abs(x - mean) for x in tp_w) / period
    if md == 0:
        return 0.0
    return (tp[-1] - mean) / (0.015 * md)


def macd_fast(closes: list) -> Tuple[float, float, float]:
    """Fast MACD (5,10,4). Returns (macd_line, signal_line, histogram)."""
    c = list(closes)
    if len(c) < 12:
        return 0, 0, 0
    e5 = ema(c[-8:], 5)
    e10 = ema(c[-15:], 10)
    if e5 is None or e10 is None:
        return 0, 0, 0
    ml = e5 - e10
    sl = ema([ml] * 4, 4) or ml
    return ml, sl, ml - sl


def atr(highs: list, lows: list, closes: list, period: int = 7) -> float:
    """Average True Range."""
    h = list(highs)
    l = list(lows)
    c = list(closes)
    if len(c) < 2:
        return 0
    tr_list = []
    for i in range(1, len(c)):
        tr_list.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    return sum(tr_list[-period:]) / min(period, len(tr_list)) if tr_list else 0


def adx(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """Average Directional Index."""
    h = list(highs)
    l = list(lows)
    c = list(closes)
    if len(c) < period + 2:
        return 0
    dm_p = []
    dm_n = []
    tr_l = []
    for i in range(1, len(c)):
        up = h[i] - h[i - 1]
        dn = l[i - 1] - l[i]
        dm_p.append(up if up > dn and up > 0 else 0)
        dm_n.append(dn if dn > up and dn > 0 else 0)
        tr_l.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    atr_v = sum(tr_l[-period:]) / period
    if atr_v == 0:
        return 0
    pdi = 100 * sum(dm_p[-period:]) / period / atr_v
    ndi = 100 * sum(dm_n[-period:]) / period / atr_v
    return round(100 * abs(pdi - ndi) / (pdi + ndi), 1) if (pdi + ndi) > 0 else 0


def price_action(opens: list, closes: list, highs: list, lows: list) -> Optional[str]:
    """Detect price action patterns (pinbar, engulfing). Returns 'BUY', 'SELL', or None."""
    o = list(opens)
    c = list(closes)
    h = list(highs)
    l = list(lows)
    if len(o) < 2:
        return None
    body = abs(c[-1] - o[-1])
    rng = h[-1] - l[-1]
    if rng == 0:
        return None
    ratio = body / rng

    # Pinbar: small body, long wick
    if ratio < 0.3:
        upper_wick = h[-1] - max(o[-1], c[-1])
        lower_wick = min(o[-1], c[-1]) - l[-1]
        if lower_wick > body * 2.5 and lower_wick > upper_wick * 1.5:
            return 'BUY'  # hammer
        if upper_wick > body * 2.5 and upper_wick > lower_wick * 1.5:
            return 'SELL'  # shooting star

    # Engulfing
    prev_body = abs(c[-2] - o[-2])
    if body > prev_body * 1.2 and rng > (h[-2] - l[-2]) * 0.8:
        if c[-1] > o[-1] and c[-2] < o[-2]:
            return 'BUY'  # bullish engulfing
        if c[-1] < o[-1] and c[-2] > o[-2]:
            return 'SELL'  # bearish engulfing

    return None


def find_sr_levels(highs: list, lows: list, lookback: int = 120) -> Tuple[list, list]:
    """Find support and resistance levels from swing points."""
    h = list(highs)
    l = list(lows)
    if len(h) < 6:
        return [], []
    if len(h) < lookback:
        lookback = len(h)
    h = h[-lookback:]
    l = l[-lookback:]
    supports = []
    resistances = []
    for i in range(2, len(h) - 2):
        if h[i] > h[i - 1] and h[i] > h[i - 2] and h[i] > h[i + 1] and h[i] > h[i + 2]:
            resistances.append(h[i])
        if l[i] < l[i - 1] and l[i] < l[i - 2] and l[i] < l[i + 1] and l[i] < l[i + 2]:
            supports.append(l[i])
    return supports, resistances


def near_level(price: float, levels: list, threshold_pct: float = 0.15) -> Optional[float]:
    """Check if price is near any S/R level."""
    for lv in levels:
        if abs(price - lv) / price * 100 < threshold_pct:
            return lv
    return None


def htf_trend(closes: list) -> Tuple[str, float]:
    """Detect higher timeframe trend using 4 criteria.
    Returns ('up'|'down'|'neutral', trend_pct)."""
    c = list(closes)
    if len(c) < 60:
        return 'neutral', 0
    ema_fast = ema(c[-30:], 30)
    ema_slow = ema(c[-80:], 80) if len(c) >= 80 else ema(c, len(c))
    price = c[-1]
    if not ema_fast or not ema_slow or ema_slow == 0:
        return 'neutral', 0
    trend_pct = (ema_fast - ema_slow) / ema_slow * 100
    slope = (c[-1] - c[-10]) / c[-10] * 100 if len(c) >= 12 else 0
    up = 0
    dn = 0
    if price > ema_fast:
        up += 1
    else:
        dn += 1
    if price > ema_slow:
        up += 1
    else:
        dn += 1
    if ema_fast > ema_slow:
        up += 1
    else:
        dn += 1
    if slope > 0.05:
        up += 1
    elif slope < -0.05:
        dn += 1
    if up >= 3:
        return 'up', trend_pct
    if dn >= 3:
        return 'down', trend_pct
    return 'neutral', trend_pct


def higher_lows(lows: list, count: int = 3) -> bool:
    """Check if recent swing lows are ascending (bullish structure)."""
    l = list(lows)
    if len(l) < 20:
        return False
    swings = []
    for i in range(2, min(len(l) - 2, 50)):
        if l[i] < l[i - 1] and l[i] < l[i - 2] and l[i] < l[i + 1] and l[i] < l[i + 2]:
            swings.append(l[i])
            if len(swings) >= count:
                break
    return len(swings) >= count and all(swings[i] > swings[i + 1] for i in range(len(swings) - 1))


def lower_highs(highs: list, count: int = 3) -> bool:
    """Check if recent swing highs are descending (bearish structure)."""
    h = list(highs)
    if len(h) < 20:
        return False
    swings = []
    for i in range(2, min(len(h) - 2, 50)):
        if h[i] > h[i - 1] and h[i] > h[i - 2] and h[i] > h[i + 1] and h[i] > h[i + 2]:
            swings.append(h[i])
            if len(swings) >= count:
                break
    return len(swings) >= count and all(swings[i] < swings[i + 1] for i in range(len(swings) - 1))
