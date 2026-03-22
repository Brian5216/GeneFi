"""Strategy Gene Model - Each strategy is an individual in the population."""
import uuid
import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StrategyGene:
    """A single strategy individual with its genetic parameters."""

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    generation: int = 0
    parent_id: Optional[str] = None
    born_at: float = field(default_factory=time.time)

    # Core Gene Parameters
    leverage: float = 1.0           # 1x - 20x
    entry_threshold: float = 0.5    # Signal strength to enter (0-1)
    exit_threshold: float = 0.3     # Signal strength to exit (0-1)
    hedge_ratio: float = 0.0        # 0 = no hedge, 1 = fully hedged
    stop_loss_pct: float = 0.05     # 5% default stop loss
    take_profit_pct: float = 0.10   # 10% default take profit
    direction: str = "long"         # "long", "short", "neutral"
    chain: str = "ethereum"         # Execution chain
    strategy_type: str = "funding_arb"  # "funding_arb", "grid", "momentum", "mean_reversion"

    # Performance Metrics (filled by Executor)
    pnl_pct: float = 0.0
    funding_yield: float = 0.0
    max_drawdown: float = 0.0
    trades_count: int = 0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0

    # Fitness Score (filled by Judge)
    fitness_score: float = 0.0
    alive: bool = True

    # Virtual Balance (each strategy starts with $10,000)
    virtual_balance: float = 10000.0
    initial_balance: float = 10000.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "born_at": self.born_at,
            "genes": {
                "leverage": self.leverage,
                "entry_threshold": self.entry_threshold,
                "exit_threshold": self.exit_threshold,
                "hedge_ratio": self.hedge_ratio,
                "stop_loss_pct": self.stop_loss_pct,
                "take_profit_pct": self.take_profit_pct,
                "direction": self.direction,
                "chain": self.chain,
                "strategy_type": self.strategy_type,
            },
            "performance": {
                "pnl_pct": self.pnl_pct,
                "funding_yield": self.funding_yield,
                "max_drawdown": self.max_drawdown,
                "trades_count": self.trades_count,
                "win_rate": self.win_rate,
                "sharpe_ratio": self.sharpe_ratio,
            },
            "fitness_score": self.fitness_score,
            "alive": self.alive,
            "virtual_balance": round(self.virtual_balance, 2),
            "balance_pnl_pct": round((self.virtual_balance / self.initial_balance - 1) * 100, 2),
        }

    @staticmethod
    def random(generation: int = 0, parent_id: Optional[str] = None) -> "StrategyGene":
        """Generate a random strategy individual."""
        directions = ["long", "short", "neutral"]
        chains = ["ethereum", "arbitrum", "optimism", "polygon", "base", "bsc"]
        types = ["funding_arb", "grid", "momentum", "mean_reversion"]

        return StrategyGene(
            generation=generation,
            parent_id=parent_id,
            leverage=round(random.uniform(1.0, 10.0), 1),
            entry_threshold=round(random.uniform(0.2, 0.9), 3),
            exit_threshold=round(random.uniform(0.1, 0.5), 3),
            hedge_ratio=round(random.uniform(0.0, 1.0), 2),
            stop_loss_pct=round(random.uniform(0.02, 0.15), 3),
            take_profit_pct=round(random.uniform(0.05, 0.30), 3),
            direction=random.choice(directions),
            chain=random.choice(chains),
            strategy_type=random.choice(types),
        )

    def mutate(self, mutation_rate: float = 0.15) -> "StrategyGene":
        """Create a mutated offspring from this strategy."""
        child = StrategyGene(
            generation=self.generation + 1,
            parent_id=self.id,
            leverage=self.leverage,
            entry_threshold=self.entry_threshold,
            exit_threshold=self.exit_threshold,
            hedge_ratio=self.hedge_ratio,
            stop_loss_pct=self.stop_loss_pct,
            take_profit_pct=self.take_profit_pct,
            direction=self.direction,
            chain=self.chain,
            strategy_type=self.strategy_type,
        )

        # Mutate numeric genes with gaussian noise
        if random.random() < mutation_rate:
            child.leverage = max(1.0, min(20.0, child.leverage + random.gauss(0, 1.5)))
        if random.random() < mutation_rate:
            child.entry_threshold = max(0.1, min(0.95, child.entry_threshold + random.gauss(0, 0.1)))
        if random.random() < mutation_rate:
            child.exit_threshold = max(0.05, min(0.6, child.exit_threshold + random.gauss(0, 0.08)))
        if random.random() < mutation_rate:
            child.hedge_ratio = max(0.0, min(1.0, child.hedge_ratio + random.gauss(0, 0.15)))
        if random.random() < mutation_rate:
            child.stop_loss_pct = max(0.01, min(0.20, child.stop_loss_pct + random.gauss(0, 0.02)))
        if random.random() < mutation_rate:
            child.take_profit_pct = max(0.03, min(0.50, child.take_profit_pct + random.gauss(0, 0.04)))

        # Occasionally flip direction, chain, or strategy type
        if random.random() < mutation_rate * 0.5:
            child.direction = random.choice(["long", "short", "neutral"])
        if random.random() < mutation_rate * 0.3:
            child.chain = random.choice(["ethereum", "arbitrum", "optimism", "polygon", "base", "bsc"])
        if random.random() < mutation_rate * 0.2:
            child.strategy_type = random.choice(["funding_arb", "grid", "momentum", "mean_reversion"])

        # Round values
        child.leverage = round(child.leverage, 1)
        child.entry_threshold = round(child.entry_threshold, 3)
        child.exit_threshold = round(child.exit_threshold, 3)
        child.hedge_ratio = round(child.hedge_ratio, 2)
        child.stop_loss_pct = round(child.stop_loss_pct, 3)
        child.take_profit_pct = round(child.take_profit_pct, 3)

        return child

    @staticmethod
    def crossover(parent_a: "StrategyGene", parent_b: "StrategyGene") -> "StrategyGene":
        """Create offspring by combining genes from two parents."""
        child = StrategyGene(
            generation=max(parent_a.generation, parent_b.generation) + 1,
            parent_id=f"{parent_a.id}+{parent_b.id}",
            leverage=random.choice([parent_a.leverage, parent_b.leverage]),
            entry_threshold=random.choice([parent_a.entry_threshold, parent_b.entry_threshold]),
            exit_threshold=random.choice([parent_a.exit_threshold, parent_b.exit_threshold]),
            hedge_ratio=(parent_a.hedge_ratio + parent_b.hedge_ratio) / 2,
            stop_loss_pct=random.choice([parent_a.stop_loss_pct, parent_b.stop_loss_pct]),
            take_profit_pct=random.choice([parent_a.take_profit_pct, parent_b.take_profit_pct]),
            direction=random.choice([parent_a.direction, parent_b.direction]),
            chain=random.choice([parent_a.chain, parent_b.chain]),
            strategy_type=random.choice([parent_a.strategy_type, parent_b.strategy_type]),
        )
        return child
