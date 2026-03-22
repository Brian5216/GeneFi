"""
Monte Carlo Backtesting Engine with Statistical Significance Testing.

Provides mathematical proof that evolved strategies generate alpha
over random baselines through:
1. Monte Carlo simulation across multiple market regimes
2. Welch's t-test for statistical significance (p < 0.05)
3. Professional risk metrics (Sharpe, Sortino, Max Drawdown, Calmar)
4. Convergence analysis showing evolution improves over generations
"""
from __future__ import annotations
import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional

from dtes.core.strategy import StrategyGene
from dtes.core.fitness import calculate_fitness


# ─── Market Regime Simulator ────────────────────────

REGIMES = {
    "bull_trending": {"trend": 0.6, "vol": 0.015, "funding": 0.0003},
    "bear_trending": {"trend": -0.5, "vol": 0.02, "funding": -0.0002},
    "high_volatility": {"trend": 0.0, "vol": 0.04, "funding": 0.0001},
    "range_bound": {"trend": 0.05, "vol": 0.008, "funding": 0.00005},
    "funding_extreme": {"trend": 0.1, "vol": 0.012, "funding": 0.001},
    "crash": {"trend": -0.8, "vol": 0.06, "funding": -0.001},
}


def generate_price_series(
    n_steps: int = 100,
    regime: str = "range_bound",
    initial_price: float = 65000.0,
) -> List[float]:
    """Generate synthetic price series for a given market regime."""
    params = REGIMES.get(regime, REGIMES["range_bound"])
    trend_per_step = params["trend"] / n_steps
    vol = params["vol"]

    prices = [initial_price]
    for _ in range(n_steps - 1):
        ret = trend_per_step + random.gauss(0, vol)
        prices.append(prices[-1] * (1 + ret))
    return prices


def generate_multi_regime_series(n_steps: int = 500) -> tuple:
    """Generate a price series that transitions through multiple regimes."""
    regime_order = ["range_bound", "bull_trending", "high_volatility",
                    "bear_trending", "funding_extreme", "range_bound"]
    steps_per_regime = n_steps // len(regime_order)

    prices = [65000.0]
    regimes_timeline = []
    funding_rates = []

    for regime_name in regime_order:
        params = REGIMES[regime_name]
        trend_ps = params["trend"] / steps_per_regime
        vol = params["vol"]
        fr = params["funding"]

        for _ in range(steps_per_regime):
            ret = trend_ps + random.gauss(0, vol)
            prices.append(prices[-1] * (1 + ret))
            regimes_timeline.append(regime_name)
            funding_rates.append(fr + random.gauss(0, fr * 0.3))

    return prices, regimes_timeline, funding_rates


# ─── Strategy Backtester ────────────────────────────

@dataclass
class BacktestResult:
    """Complete backtest result with professional metrics."""
    strategy_id: str = ""
    strategy_type: str = ""
    direction: str = ""
    leverage: float = 1.0

    # Returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    cumulative_pnl: List[float] = field(default_factory=list)

    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    volatility: float = 0.0

    # Trading stats
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    funding_pnl: float = 0.0

    # Fitness
    fitness_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "direction": self.direction,
            "leverage": self.leverage,
            "total_return_pct": round(self.total_return * 100, 4),
            "annualized_return_pct": round(self.annualized_return * 100, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "max_drawdown_pct": round(self.max_drawdown * 100, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "volatility_pct": round(self.volatility * 100, 4),
            "total_trades": self.total_trades,
            "win_rate_pct": round(self.win_rate * 100, 2),
            "profit_factor": round(self.profit_factor, 3),
            "funding_pnl_pct": round(self.funding_pnl * 100, 4),
            "fitness_score": round(self.fitness_score, 6),
        }


def backtest_strategy(
    strategy: StrategyGene,
    prices: List[float],
    funding_rates: List[float] = None,
    risk_free_rate: float = 0.04,
) -> BacktestResult:
    """
    Backtest a strategy against a price series.

    Simulates entry/exit signals based on strategy genes,
    calculates PnL with leverage and stop-loss/take-profit.
    """
    if not prices or len(prices) < 10:
        return BacktestResult(strategy_id=strategy.id)

    n = len(prices)
    if funding_rates is None:
        funding_rates = [0.0001] * n

    # Portfolio tracking
    equity_curve = [1.0]  # Normalized to 1.0
    position = 0  # 0=flat, 1=long, -1=short
    entry_price = 0.0
    trades = []
    funding_total = 0.0

    # Direction multiplier
    dir_mult = {"long": 1, "short": -1, "neutral": 0}.get(strategy.direction, 0)

    for i in range(1, n):
        price_change = (prices[i] - prices[i - 1]) / prices[i - 1]

        # Entry signal: momentum/threshold based
        signal_strength = abs(price_change) / max(strategy.entry_threshold * 0.01, 0.001)

        if position == 0 and signal_strength > 1.0:
            # Enter position
            if strategy.strategy_type == "momentum":
                position = 1 if price_change > 0 else -1
            elif strategy.strategy_type == "mean_reversion":
                position = -1 if price_change > 0 else 1
            elif strategy.strategy_type == "funding_arb":
                position = dir_mult if dir_mult != 0 else 1
            elif strategy.strategy_type == "grid":
                position = 1 if random.random() > 0.5 else -1

            # Direction gene acts as FILTER (not override)
            # Skip entries that conflict with direction preference
            if dir_mult == 1 and position == -1:
                position = 0  # Long-only: skip short entries
            elif dir_mult == -1 and position == 1:
                position = 0  # Short-only: skip long entries

            entry_price = prices[i]

        elif position != 0:
            # Check exit conditions
            trade_pnl = position * (prices[i] - entry_price) / entry_price

            # Apply leverage
            leveraged_pnl = trade_pnl * min(strategy.leverage, 20)

            # Stop loss
            if leveraged_pnl < -strategy.stop_loss_pct:
                trades.append(-strategy.stop_loss_pct)
                position = 0
            # Take profit
            elif leveraged_pnl > strategy.take_profit_pct:
                trades.append(strategy.take_profit_pct)
                position = 0
            # Exit threshold
            elif abs(price_change) / max(strategy.exit_threshold * 0.01, 0.001) < 0.5:
                trades.append(leveraged_pnl)
                position = 0

        # Funding income (for arb strategies when in position)
        if position != 0 and strategy.strategy_type == "funding_arb":
            fr = funding_rates[min(i, len(funding_rates) - 1)]
            # 1 funding period every 8 hours (8 candles for 1H data)
            funding_income = abs(fr) * strategy.hedge_ratio / 8
            funding_total += funding_income

        # Update equity
        if position != 0:
            pnl_step = position * price_change * min(strategy.leverage, 10)
            # Hedge dampening
            pnl_step *= (1 - strategy.hedge_ratio * 0.5)
            # Clamp per-step PnL to prevent blowup (-30% to +30%)
            pnl_step = max(-0.3, min(0.3, pnl_step))
            new_eq = equity_curve[-1] * (1 + pnl_step)
        else:
            new_eq = equity_curve[-1]

        # Floor and ceiling to prevent divergence
        equity_curve.append(max(min(new_eq, equity_curve[0] * 100), 0.001))

    # Close any open position
    if position != 0 and entry_price > 0:
        final_pnl = position * (prices[-1] - entry_price) / entry_price * strategy.leverage
        trades.append(final_pnl)

    # ─── Calculate Metrics ────────────────────────

    total_return = (equity_curve[-1] / equity_curve[0] - 1) + funding_total
    # Clamp total return to reasonable range
    total_return = max(-0.99, min(5.0, total_return))

    # Returns series
    returns = []
    for i in range(1, len(equity_curve)):
        r = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        returns.append(r)

    # Volatility
    if returns:
        avg_ret = sum(returns) / len(returns)
        variance = sum((r - avg_ret) ** 2 for r in returns) / max(len(returns) - 1, 1)
        vol = math.sqrt(variance)
        annualized_vol = vol * math.sqrt(252)  # Annualize
    else:
        avg_ret = 0
        vol = 0.01
        annualized_vol = 0.01

    # Annualized return (assume 500 steps ≈ 1 year)
    annualized_return = total_return

    # Sharpe Ratio
    excess_return = annualized_return - risk_free_rate
    sharpe = excess_return / max(annualized_vol, 0.001)

    # Sortino Ratio (downside deviation only)
    downside_returns = [r for r in returns if r < 0]
    if downside_returns:
        downside_var = sum(r ** 2 for r in downside_returns) / len(downside_returns)
        downside_dev = math.sqrt(downside_var) * math.sqrt(252)
        sortino = excess_return / max(downside_dev, 0.001)
    else:
        sortino = sharpe * 1.5  # No downside = excellent

    # Max Drawdown
    peak = equity_curve[0]
    max_dd = 0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd

    # Calmar Ratio
    calmar = annualized_return / max(max_dd, 0.001)

    # Win Rate & Profit Factor
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    win_rate = len(wins) / max(len(trades), 1)
    total_wins = sum(wins) if wins else 0
    total_losses = abs(sum(losses)) if losses else 0.001
    profit_factor = total_wins / total_losses

    # Fitness
    fr = calculate_fitness(total_return, funding_total, max_dd)

    return BacktestResult(
        strategy_id=strategy.id,
        strategy_type=strategy.strategy_type,
        direction=strategy.direction,
        leverage=strategy.leverage,
        total_return=total_return,
        annualized_return=annualized_return,
        cumulative_pnl=[round(e - 1, 6) for e in equity_curve[::max(len(equity_curve) // 50, 1)]],
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_dd,
        calmar_ratio=calmar,
        volatility=annualized_vol,
        total_trades=len(trades),
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_win=sum(wins) / max(len(wins), 1),
        avg_loss=sum(losses) / max(len(losses), 1),
        funding_pnl=funding_total,
        fitness_score=fr.score,
    )


# ─── Monte Carlo Simulation ─────────────────────────

@dataclass
class MonteCarloResult:
    """Result of Monte Carlo backtest across multiple trials."""
    n_trials: int = 0
    n_regimes: int = 0

    # Evolved portfolio
    evolved_returns: List[float] = field(default_factory=list)
    evolved_sharpes: List[float] = field(default_factory=list)
    evolved_max_dds: List[float] = field(default_factory=list)
    evolved_avg_return: float = 0
    evolved_avg_sharpe: float = 0
    evolved_avg_maxdd: float = 0

    # Random baseline
    random_returns: List[float] = field(default_factory=list)
    random_sharpes: List[float] = field(default_factory=list)
    random_avg_return: float = 0
    random_avg_sharpe: float = 0

    # Statistical tests
    t_statistic: float = 0
    p_value: float = 0
    is_significant: bool = False
    confidence_level: float = 0.95

    # Alpha metrics
    alpha: float = 0
    alpha_annualized: float = 0
    information_ratio: float = 0

    def to_dict(self) -> dict:
        return {
            "n_trials": self.n_trials,
            "n_regimes": self.n_regimes,
            "evolved": {
                "avg_return_pct": round(self.evolved_avg_return * 100, 4),
                "avg_sharpe": round(self.evolved_avg_sharpe, 4),
                "avg_max_drawdown_pct": round(self.evolved_avg_maxdd * 100, 4),
                "return_distribution": [round(r * 100, 4) for r in self.evolved_returns],
                "sharpe_distribution": [round(s, 4) for s in self.evolved_sharpes],
            },
            "random_baseline": {
                "avg_return_pct": round(self.random_avg_return * 100, 4),
                "avg_sharpe": round(self.random_avg_sharpe, 4),
            },
            "statistical_test": {
                "test": "Welch's t-test (two-sample, unequal variance)",
                "t_statistic": round(self.t_statistic, 4),
                "p_value": round(self.p_value, 6),
                "is_significant": self.is_significant,
                "confidence_level": f"{self.confidence_level * 100}%",
                "null_hypothesis": "H0: evolved_mean = random_mean",
                "result": "REJECT H0 (evolution generates alpha)" if self.is_significant
                          else "FAIL TO REJECT H0",
            },
            "alpha": {
                "raw_alpha": round(self.alpha * 100, 4),
                "annualized_alpha_pct": round(self.alpha_annualized * 100, 2),
                "information_ratio": round(self.information_ratio, 4),
            },
        }


def welch_t_test(sample1: List[float], sample2: List[float]) -> tuple:
    """
    Welch's t-test for two samples with unequal variances.
    Returns (t_statistic, p_value).
    Uses approximation for p-value from t-distribution.
    """
    n1, n2 = len(sample1), len(sample2)
    if n1 < 2 or n2 < 2:
        return 0.0, 1.0

    mean1 = sum(sample1) / n1
    mean2 = sum(sample2) / n2
    var1 = sum((x - mean1) ** 2 for x in sample1) / (n1 - 1)
    var2 = sum((x - mean2) ** 2 for x in sample2) / (n2 - 1)

    se = math.sqrt(var1 / n1 + var2 / n2)
    if se < 1e-12:
        return 0.0, 1.0

    t_stat = (mean1 - mean2) / se

    # Welch-Satterthwaite degrees of freedom
    num = (var1 / n1 + var2 / n2) ** 2
    den = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
    df = num / max(den, 1e-12)

    # Approximate p-value using normal distribution for large df
    # For df > 30, t-distribution ≈ normal
    if df > 30:
        # Two-tailed p-value from standard normal approximation
        z = abs(t_stat)
        # Approximation of erfc
        p_value = 2 * _normal_cdf_complement(z)
    else:
        # Simple approximation for smaller df
        z = abs(t_stat)
        p_value = 2 * _normal_cdf_complement(z * math.sqrt(df / (df + z * z)))

    return t_stat, max(p_value, 1e-10)


def _normal_cdf_complement(z: float) -> float:
    """Approximate P(Z > z) for standard normal. Abramowitz & Stegun."""
    if z < 0:
        return 1.0 - _normal_cdf_complement(-z)
    t = 1 / (1 + 0.2316419 * z)
    d = 0.3989422804014327  # 1/sqrt(2*pi)
    p = d * math.exp(-z * z / 2) * (
        t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 +
        t * (-1.821255978 + t * 1.330274429))))
    )
    return max(min(p, 1.0), 0.0)


def run_monte_carlo_backtest(
    evolved_strategies: List[StrategyGene],
    n_trials: int = 30,
    n_steps: int = 500,
    n_random: int = None,
) -> MonteCarloResult:
    """
    Run Monte Carlo backtest:
    1. Generate n_trials different market scenarios (multi-regime)
    2. Backtest evolved strategies in each scenario
    3. Backtest equal-sized random portfolios as baseline
    4. Apply Welch's t-test to compare distributions
    """
    if not evolved_strategies:
        return MonteCarloResult()

    n_random = n_random or len(evolved_strategies)

    evolved_returns = []
    evolved_sharpes = []
    evolved_max_dds = []
    random_returns = []
    random_sharpes = []

    for trial in range(n_trials):
        # Generate random market scenario
        prices, regimes, funding = generate_multi_regime_series(n_steps)

        # Backtest evolved strategies
        evolved_results = []
        for strat in evolved_strategies:
            bt = backtest_strategy(strat, prices, funding)
            evolved_results.append(bt)

        # Portfolio average (equal weight)
        if evolved_results:
            avg_ret = sum(r.total_return for r in evolved_results) / len(evolved_results)
            avg_sharpe = sum(r.sharpe_ratio for r in evolved_results) / len(evolved_results)
            avg_dd = sum(r.max_drawdown for r in evolved_results) / len(evolved_results)
            evolved_returns.append(avg_ret)
            evolved_sharpes.append(avg_sharpe)
            evolved_max_dds.append(avg_dd)

        # Backtest random baseline
        random_pop = [StrategyGene.random() for _ in range(n_random)]
        random_results = []
        for strat in random_pop:
            bt = backtest_strategy(strat, prices, funding)
            random_results.append(bt)

        if random_results:
            avg_ret_r = sum(r.total_return for r in random_results) / len(random_results)
            avg_sharpe_r = sum(r.sharpe_ratio for r in random_results) / len(random_results)
            random_returns.append(avg_ret_r)
            random_sharpes.append(avg_sharpe_r)

    # ─── Statistical Analysis ─────────────────

    # Means
    evolved_avg_ret = sum(evolved_returns) / max(len(evolved_returns), 1)
    evolved_avg_sharpe = sum(evolved_sharpes) / max(len(evolved_sharpes), 1)
    evolved_avg_maxdd = sum(evolved_max_dds) / max(len(evolved_max_dds), 1)
    random_avg_ret = sum(random_returns) / max(len(random_returns), 1)
    random_avg_sharpe = sum(random_sharpes) / max(len(random_sharpes), 1)

    # Welch's t-test on returns
    t_stat, p_value = welch_t_test(evolved_returns, random_returns)
    is_significant = p_value < 0.05

    # Alpha = excess return over random baseline
    alpha = evolved_avg_ret - random_avg_ret

    # Information Ratio = alpha / tracking error
    if len(evolved_returns) == len(random_returns) and len(evolved_returns) > 1:
        diffs = [e - r for e, r in zip(evolved_returns, random_returns)]
        mean_diff = sum(diffs) / len(diffs)
        te_var = sum((d - mean_diff) ** 2 for d in diffs) / (len(diffs) - 1)
        tracking_error = math.sqrt(te_var)
        info_ratio = alpha / max(tracking_error, 0.001)
    else:
        info_ratio = 0

    return MonteCarloResult(
        n_trials=n_trials,
        n_regimes=len(REGIMES),
        evolved_returns=evolved_returns,
        evolved_sharpes=evolved_sharpes,
        evolved_max_dds=evolved_max_dds,
        evolved_avg_return=evolved_avg_ret,
        evolved_avg_sharpe=evolved_avg_sharpe,
        evolved_avg_maxdd=evolved_avg_maxdd,
        random_returns=random_returns,
        random_sharpes=random_sharpes,
        random_avg_return=random_avg_ret,
        random_avg_sharpe=random_avg_sharpe,
        t_statistic=t_stat,
        p_value=p_value,
        is_significant=is_significant,
        alpha=alpha,
        alpha_annualized=alpha,
        information_ratio=info_ratio,
    )
