"""Judge Agent - Evolution Arbiter.

Uses Claw Sonnet for structured scoring and logical mutation decisions.
Implements genetic selection: eliminate, preserve, mutate.
Triggers safe mode (OKX Earn) when population fitness degrades.
"""
from typing import Optional

from dtes.agents.base import BaseAgent
from dtes.core.strategy import StrategyGene
from dtes.core.fitness import calculate_fitness, rank_population
from dtes.protocol.a2a import MessageType, MessageBus, A2AMessage
from config import Config


# Risk thresholds
SAFE_MODE_CONSECUTIVE_DECLINE = 3
SAFE_MODE_AVG_FITNESS_THRESHOLD = -0.02


class JudgeAgent(BaseAgent):
    """
    进化裁判 - Evaluates fitness and drives evolution.

    Responsibilities:
    - Score strategy fitness using the GeneFi fitness model
    - Rank and classify strategies (elite / survive / eliminate)
    - Issue evolution directives to Predictor
    - Monitor population health and trigger OKX Earn safe mode
    """

    def __init__(self, bus: MessageBus, config: Optional[Config] = None):
        super().__init__("judge", bus)
        self.config = config or Config()
        self.fitness_history: list[float] = []
        self.safe_mode_active: bool = False
        self.consecutive_declines: int = 0

    async def handle_message(self, message: A2AMessage):
        if message.msg_type == MessageType.EXECUTION_REPORT:
            pass  # Acknowledged; scoring happens in evaluate_population()

    async def evaluate_population(
        self,
        population: list[StrategyGene],
        market_data: Optional[dict] = None,
    ) -> list[StrategyGene]:
        """
        Evaluate all strategies and assign fitness scores.

        Uses Claw Sonnet for reasoning in production mode.
        """
        for strategy in population:
            result = calculate_fitness(
                pnl_pct=strategy.pnl_pct,
                funding_yield=strategy.funding_yield,
                max_drawdown=strategy.max_drawdown,
                w_pnl=self.config.PNL_WEIGHT,
                w_funding=self.config.FUNDING_WEIGHT,
                w_drawdown=self.config.DRAWDOWN_WEIGHT,
            )
            strategy.fitness_score = result.score

        # Rank population
        ranked = rank_population(population, self.config.SELECTION_PRESSURE)

        # Track population health
        avg_fitness = sum(s.fitness_score for s in population) / len(population) if population else 0
        self.fitness_history.append(avg_fitness)
        self._check_population_health(avg_fitness)

        # Build evolution summary
        elite_ids = []
        eliminated_ids = []
        for strategy, result in ranked:
            if result.recommendation == "elite":
                elite_ids.append(strategy.id)
            elif result.recommendation == "eliminate":
                eliminated_ids.append(strategy.id)

        # Send evolution directive to Predictor
        directive_payload = {
            "avg_fitness": round(avg_fitness, 6),
            "best_strategy": ranked[0][0].id if ranked else None,
            "elite_ids": elite_ids,
            "eliminated_ids": eliminated_ids,
            "safe_mode": self.safe_mode_active,
            "new_candidates_requested": len(eliminated_ids),
            "recommendation": self._generate_recommendation(ranked, market_data),
        }

        await self.send(
            MessageType.EVOLUTION_DIRECTIVE,
            receiver="broadcast",
            payload=directive_payload,
            generation=population[0].generation if population else 0,
        )

        # Trigger safe mode if needed
        if self.safe_mode_active:
            # Execute real Earn switch if API available
            earn_result = await self._execute_safe_mode()
            await self.send(
                MessageType.SAFE_MODE_TRIGGER,
                receiver="broadcast",
                payload={
                    "reason": "Population fitness consecutive decline",
                    "consecutive_declines": self.consecutive_declines,
                    "avg_fitness": round(avg_fitness, 6),
                    "action": "Switch to OKX Earn stable mode",
                    "earn_result": earn_result,
                },
            )

        return population

    def _check_population_health(self, avg_fitness: float):
        """Monitor population health and trigger safe mode if degrading."""
        if len(self.fitness_history) >= 2:
            if self.fitness_history[-1] < self.fitness_history[-2]:
                self.consecutive_declines += 1
            else:
                self.consecutive_declines = 0

        if (
            self.consecutive_declines >= SAFE_MODE_CONSECUTIVE_DECLINE
            or avg_fitness < SAFE_MODE_AVG_FITNESS_THRESHOLD
        ):
            self.safe_mode_active = True
        else:
            self.safe_mode_active = False

    async def _execute_safe_mode(self) -> dict:
        """Execute OKX Earn switch — real API when available."""
        from dtes.okx.onchain_os import OnchainOSClient
        okx = OnchainOSClient(self.config)
        try:
            result = await okx.switch_to_earn(
                amount=self.config.MAX_POSITION_SIZE,
                product="simple_earn",
            )
            return result
        except Exception as e:
            print(f"[Judge] Earn switch failed: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            await okx.close()

    def _generate_recommendation(
        self, ranked: list, market_data: Optional[dict]
    ) -> str:
        """Generate evolution recommendation (Claw Sonnet in production)."""
        if not ranked:
            return "No strategies to evaluate."

        best = ranked[0][0]
        worst = ranked[-1][0]

        parts = [
            f"Best strategy [{best.id}]: {best.strategy_type}/{best.direction}, "
            f"fitness={best.fitness_score:.4f}, PnL={best.pnl_pct:.2%}",
            f"Worst strategy [{worst.id}]: {worst.strategy_type}/{worst.direction}, "
            f"fitness={worst.fitness_score:.4f}, PnL={worst.pnl_pct:.2%}",
        ]

        if self.safe_mode_active:
            parts.append(
                "WARNING: Population health degrading. "
                "Recommend switching to OKX Earn safe mode."
            )

        # Analyze dominant traits
        directions = {}
        for s, _ in ranked[:5]:
            directions[s.direction] = directions.get(s.direction, 0) + 1
        dominant = max(directions, key=directions.get)
        parts.append(f"Top-5 dominant direction: {dominant}")

        return " | ".join(parts)
