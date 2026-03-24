"""
CryptoEdge Pro — Trail Stop Module
Progressive trailing stop with 6 levels of profit protection.
Pure logic — no Binance API calls, no side effects.
"""

from typing import Optional, Tuple, Dict


# Default trail configuration
DEFAULT_TRAIL_CONFIG = {
    'L1': 0.50,  # trigger %
    'L2': 0.70,
    'L3': 1.00,
    'L4': 1.50,
    'L5': 2.50,
    'L6': 4.00,
    'gaps': [0, 0.08, 0.15, 0.20, 0.30, 0.40, 0.60],
    'be_buf': 0.02,
    'fee_rate': 0.0005,
    'slippage_pct': 0.03,
}

LEVEL_NAMES = {1: 'Custos', 2: 'Lucro+', 3: 'Sólido', 4: 'Forte', 5: 'Alto', 6: 'Máximo'}


def calc_cost_floor(fee_rate: float, slippage_pct: float, be_buf: float) -> float:
    """Minimum lock offset to cover costs (fee round-trip + slippage + buffer)."""
    return fee_rate * 2 * 100 + slippage_pct + be_buf


def calc_lock_offset(trigger: float, gap: float, cost_floor: float) -> float:
    """K = lock offset. Where trail SL sits. Max of (trigger - gap, cost_floor)."""
    return max(trigger - gap, cost_floor)


def build_trail_table(config: dict = None) -> list:
    """Build trail table: [(level, trigger, lock_offset), ...] sorted by level DESC."""
    cfg = config or DEFAULT_TRAIL_CONFIG
    cost_floor = calc_cost_floor(cfg.get('fee_rate', 0.0005),
                                  cfg.get('slippage_pct', 0.03),
                                  cfg.get('be_buf', 0.02))
    gaps = cfg.get('gaps', DEFAULT_TRAIL_CONFIG['gaps'])
    levels = [
        (1, cfg.get('L1', 0.30), gaps[1]),
        (2, cfg.get('L2', 0.50), gaps[2]),
        (3, cfg.get('L3', 0.80), gaps[3]),
        (4, cfg.get('L4', 1.20), gaps[4]),
        (5, cfg.get('L5', 2.00), gaps[5]),
        (6, cfg.get('L6', 3.00), gaps[6]),
    ]
    table = []
    for lv, trigger, gap in levels:
        lock = calc_lock_offset(trigger, gap, cost_floor)
        table.append((lv, trigger, lock))
    # Sort by level DESC (check highest first)
    table.sort(key=lambda x: x[0], reverse=True)
    return table


def evaluate_trail(
    pnl_pct: float,
    entry: float,
    side: str,
    cur_level: int,
    cur_trail_sl: Optional[float],
    trail_table: list,
    dyn_gaps: dict = None,
) -> Tuple[int, Optional[float], bool]:
    """
    Evaluate trail stop position based on current PnL.

    Returns: (new_level, new_trail_sl, level_changed)
    """
    new_level = cur_level
    new_tsl = cur_trail_sl

    # Static trail: check each level
    for lv, trigger, lock_offset in trail_table:
        if pnl_pct >= trigger:
            cand = entry * (1 + lock_offset / 100) if side == 'BUY' else entry * (1 - lock_offset / 100)
            # Trail NEVER moves backward
            if side == 'BUY' and (cur_trail_sl is None or cand > (new_tsl or 0)):
                new_tsl = cand
                new_level = max(new_level, lv)
            elif side == 'SELL' and (cur_trail_sl is None or cand < (new_tsl or float('inf'))):
                new_tsl = cand
                new_level = max(new_level, lv)
            break  # first match (highest level) wins

    # Dynamic trail for L4+: follows price at fixed distance
    if cur_level >= 4 and pnl_pct > 0 and dyn_gaps:
        trail_dist = dyn_gaps.get(cur_level, 0.35)
        dyn_lock = pnl_pct - trail_dist
        if dyn_lock > 0:
            dyn = entry * (1 + dyn_lock / 100) if side == 'BUY' else entry * (1 - dyn_lock / 100)
            if side == 'BUY' and (new_tsl is None or dyn > new_tsl):
                new_tsl = dyn
            elif side == 'SELL' and (new_tsl is None or dyn < new_tsl):
                new_tsl = dyn

    level_changed = new_level > cur_level
    return new_level, new_tsl, level_changed


def calc_active_sl(side: str, sl_orig: float, trail_sl: Optional[float]) -> float:
    """Calculate active SL = best of original SL and trail SL."""
    if trail_sl is None:
        return sl_orig
    if side == 'BUY':
        return max(sl_orig, trail_sl)
    else:
        return min(sl_orig, trail_sl)


def should_close(side: str, price: float, active_sl: float, tp: float,
                 no_tp_ceiling: bool, pnl_pct: float, age_sec: float,
                 time_exit: float) -> Optional[str]:
    """
    Determine if position should be closed.
    Returns reason string if should close, None if should stay open.
    Implements progressive loss cutting:
    - 45min in loss + < -0.25% → cut
    - 90min in loss + < -0.15% → cut  
    - 120min in loss → cut any loss
    """
    if side == 'BUY':
        if not no_tp_ceiling and price >= tp:
            return f'TP'
        if price <= active_sl:
            return 'trail_hit'
    else:
        if not no_tp_ceiling and price <= tp:
            return f'TP'
        if price >= active_sl:
            return 'trail_hit'

    # Progressive loss cutting
    if pnl_pct <= 0:
        if age_sec > 2700 and pnl_pct < -0.25:
            return f'Loss-cut 45m ({pnl_pct:+.2f}%)'
        if age_sec > 5400 and pnl_pct < -0.15:
            return f'Loss-cut 90m ({pnl_pct:+.2f}%)'
        if age_sec > 7200:
            return f'Time-exit 2h ({pnl_pct:+.2f}%)'

    # Profit but no trail after 4h
    if pnl_pct > 0 and age_sec > time_exit * 2:
        return f'Time-exit profit ({pnl_pct:+.2f}%)'

    return None
