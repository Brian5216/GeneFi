"""Predictor Agent - Population Incubator.

Generates initial strategy populations and creates new candidates
based on market data and Claw Opus reasoning.
Uses OKX OnchainOS AI Skills for real-time market intelligence.
"""
import random
from typing import Optional

from dtes.agents.base import BaseAgent
from dtes.core.strategy import StrategyGene
from dtes.protocol.a2a import MessageType, MessageBus, A2AMessage
from config import Config


# Market regime detection thresholds
REGIME_THRESHOLDS = {
    "high_vol": 0.03,      # Daily vol > 3%
    "funding_extreme": 0.001,  # |Funding| > 0.1%
}


class PredictorAgent(BaseAgent):
    """
    种群孵化器 - Generates and manages strategy populations.

    Responsibilities:
    - Generate initial random population (Genesis)
    - Create market-aware strategy candidates based on OnchainOS data
    - Adapt population direction based on Judge's evolution directives
    - Detect market regime shifts and trigger population pivots
    """

    def __init__(self, bus: MessageBus, config: Optional[Config] = None):
        super().__init__("predictor", bus)
        self.config = config or Config()
        self.market_state: dict = {}
        self.generation_directives: list = []

    async def handle_message(self, message: A2AMessage):
        if message.msg_type == MessageType.EVOLUTION_DIRECTIVE:
            self.generation_directives.append(message.payload)
        elif message.msg_type == MessageType.MARKET_UPDATE:
            self.market_state = message.payload

    async def generate_population(
        self,
        existing: list[StrategyGene],
        market_data: Optional[dict] = None,
    ) -> list[StrategyGene]:
        """
        Generate new strategy candidates for the population.

        In demo mode, creates market-aware strategies.
        In production, would call Claw Opus via MCP for reasoning.
        """
        market_data = market_data or self.market_state
        regime = self._detect_regime(market_data)

        new_candidates = []
        candidates_needed = max(0, self.config.POPULATION_SIZE - len(existing))

        if candidates_needed == 0 and self.generation_directives:
            # Judge requested specific types of mutations
            directive = self.generation_directives[-1]
            candidates_needed = directive.get("new_candidates_requested", 3)

        for _ in range(candidates_needed):
            candidate = self._create_market_aware_strategy(regime, market_data)
            new_candidates.append(candidate)

        # Send strategy batch to Executor
        if new_candidates:
            await self.send(
                MessageType.STRATEGY_BATCH,
                receiver="broadcast",
                payload={
                    "candidates": [s.to_dict() for s in new_candidates],
                    "regime": regime,
                    "reasoning": self._generate_reasoning(regime, market_data),
                },
                generation=new_candidates[0].generation if new_candidates else 0,
            )

        return new_candidates

    def _detect_regime(self, market_data: Optional[dict]) -> str:
        """Detect current market regime from OnchainOS data."""
        if not market_data:
            return "normal"

        volatility = market_data.get("volatility", 0.02)
        funding_rate = market_data.get("funding_rate", 0.0001)
        trend = market_data.get("trend", 0)

        if volatility > REGIME_THRESHOLDS["high_vol"]:
            if trend > 0.5:
                return "bull_volatile"
            elif trend < -0.5:
                return "bear_volatile"
            return "high_volatility"

        if abs(funding_rate) > REGIME_THRESHOLDS["funding_extreme"]:
            return "funding_extreme_positive" if funding_rate > 0 else "funding_extreme_negative"

        if abs(trend) < 0.2:
            return "range_bound"

        return "trending_up" if trend > 0 else "trending_down"

    def _create_market_aware_strategy(
        self, regime: str, market_data: Optional[dict]
    ) -> StrategyGene:
        """Create a strategy adapted to current market regime."""
        strategy = StrategyGene.random(generation=0)

        # Regime-specific parameter tuning
        if regime in ("bull_volatile", "trending_up"):
            strategy.direction = random.choice(["long", "long", "neutral"])
            strategy.leverage = round(random.uniform(2.0, 8.0), 1)
            strategy.stop_loss_pct = round(random.uniform(0.03, 0.08), 3)

        elif regime in ("bear_volatile", "trending_down"):
            strategy.direction = random.choice(["short", "short", "neutral"])
            strategy.leverage = round(random.uniform(2.0, 6.0), 1)
            strategy.hedge_ratio = round(random.uniform(0.3, 0.8), 2)

        elif regime == "funding_extreme_positive":
            strategy.strategy_type = "funding_arb"
            strategy.direction = "short"
            strategy.hedge_ratio = round(random.uniform(0.8, 1.0), 2)
            strategy.leverage = round(random.uniform(1.0, 3.0), 1)

        elif regime == "funding_extreme_negative":
            strategy.strategy_type = "funding_arb"
            strategy.direction = "long"
            strategy.hedge_ratio = round(random.uniform(0.8, 1.0), 2)
            strategy.leverage = round(random.uniform(1.0, 3.0), 1)

        elif regime == "range_bound":
            strategy.strategy_type = random.choice(["grid", "mean_reversion"])
            strategy.direction = "neutral"
            strategy.leverage = round(random.uniform(1.0, 3.0), 1)

        elif regime == "high_volatility":
            strategy.stop_loss_pct = round(random.uniform(0.05, 0.12), 3)
            strategy.take_profit_pct = round(random.uniform(0.10, 0.25), 3)
            strategy.leverage = round(random.uniform(1.0, 4.0), 1)

        return strategy

    def _generate_reasoning(self, regime: str, market_data: Optional[dict]) -> str:
        """Generate reasoning text for audit trail (Claw Opus in production)."""
        reasoning_map = {
            "bull_volatile": "High volatility with upward trend detected. Generating long-biased strategies with moderate leverage.",
            "bear_volatile": "Bearish volatility detected. Generating short-biased strategies with hedging.",
            "trending_up": "Sustained uptrend. Generating momentum-following long strategies.",
            "trending_down": "Downtrend in progress. Generating short and hedged strategies.",
            "funding_extreme_positive": "Extreme positive funding rate. Generating funding arbitrage shorts with full hedge.",
            "funding_extreme_negative": "Extreme negative funding rate. Generating funding arbitrage longs with full hedge.",
            "range_bound": "Market in consolidation. Generating grid and mean reversion strategies.",
            "high_volatility": "High volatility without clear direction. Widening stops and reducing leverage.",
            "normal": "Normal market conditions. Generating diversified strategy mix.",
        }
        return reasoning_map.get(regime, "Generating diversified strategy population.")
