"""Fitness Scoring Model for Strategy Evaluation."""
from dataclasses import dataclass


@dataclass
class FitnessResult:
    score: float
    pnl_component: float
    funding_component: float
    drawdown_penalty: float
    rank: int = 0
    recommendation: str = "hold"  # "survive", "eliminate", "elite"


def calculate_fitness(
    pnl_pct: float,
    funding_yield: float,
    max_drawdown: float,
    w_pnl: float = 0.5,
    w_funding: float = 0.3,
    w_drawdown: float = 0.2,
) -> FitnessResult:
    """
    GeneFi Fitness Function:
    Score = w_pnl × PnL% + w_funding × FundingYield - w_drawdown × MaxDrawdown

    All components normalized to comparable scales.
    """
    pnl_component = w_pnl * pnl_pct
    # Normalize funding_yield to comparable scale with pnl_pct
    # Typical funding_yield ~0.0003, pnl_pct ~0.05, ratio ~100x
    funding_component = w_funding * (funding_yield * 50)
    drawdown_penalty = w_drawdown * max_drawdown

    score = pnl_component + funding_component - drawdown_penalty

    return FitnessResult(
        score=round(score, 6),
        pnl_component=round(pnl_component, 6),
        funding_component=round(funding_component, 6),
        drawdown_penalty=round(drawdown_penalty, 6),
    )


def rank_population(strategies: list, selection_pressure: float = 0.3) -> list:
    """
    Rank strategies and assign survival recommendations.

    Top tier (top 20%): "elite" - preserved and used as parents
    Middle tier (20%-70%): "survive" - kept but may be replaced
    Bottom tier (bottom 30%): "eliminate" - removed from population
    """
    sorted_strategies = sorted(strategies, key=lambda s: s.fitness_score, reverse=True)
    n = len(sorted_strategies)

    elite_cutoff = int(n * 0.2)
    eliminate_cutoff = int(n * (1 - selection_pressure))

    results = []
    for i, strategy in enumerate(sorted_strategies):
        result = FitnessResult(
            score=strategy.fitness_score,
            pnl_component=0,
            funding_component=0,
            drawdown_penalty=0,
            rank=i + 1,
        )
        if i < elite_cutoff:
            result.recommendation = "elite"
        elif i < eliminate_cutoff:
            result.recommendation = "survive"
        else:
            result.recommendation = "eliminate"
        results.append((strategy, result))

    return results
