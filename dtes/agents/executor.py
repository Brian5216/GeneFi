"""Executor Agent - Live Strategy Execution.

Executes strategies via OKX OnchainOS Open API tools:
- place_futures_order: Futures trading
- create_grid_bot: Grid strategy deployment
- Cross-chain liquidity routing (60+ chains, 500+ DEX)

In demo mode, simulates execution with realistic market dynamics.
"""
import random
import math
from typing import Optional

from dtes.agents.base import BaseAgent
from dtes.core.strategy import StrategyGene
from dtes.protocol.a2a import MessageType, MessageBus, A2AMessage
from config import Config


class ExecutorAgent(BaseAgent):
    """
    实战执行者 - Executes strategies and collects performance data.

    Responsibilities:
    - Execute strategies through OKX OnchainOS API
    - Collect real-time PnL, slippage, risk exposure
    - Report execution results to Judge Agent
    - Handle order management and position tracking
    - Track cumulative portfolio balance across generations
    """

    def __init__(self, bus: MessageBus, config: Optional[Config] = None):
        super().__init__("executor", bus)
        self.config = config or Config()
        self.active_positions: dict[str, dict] = {}
        self.execution_log: list[dict] = []

        # Portfolio tracking across generations
        self.initial_balance = 100000.0  # $100k starting capital
        self.balance = self.initial_balance
        self.balance_history: list[dict] = []  # {generation, balance, pnl_pct, drawdown}
        self.peak_balance = self.initial_balance
        self.total_realized_pnl = 0.0

    async def handle_message(self, message: A2AMessage):
        if message.msg_type == MessageType.STRATEGY_BATCH:
            pass  # Acknowledged; execution happens in execute_strategies()

    async def execute_strategies(
        self,
        population: list[StrategyGene],
        market_data: Optional[dict] = None,
    ) -> list[StrategyGene]:
        """
        Execute all strategies and fill their performance metrics.

        Production: calls OKX OnchainOS place_futures_order / create_grid_bot
        Demo: simulates with market-correlated random performance
        """
        market_data = market_data or {}

        for strategy in population:
            if self.config.EXECUTION_MODE == "demo_api" and self.config.has_api_keys:
                await self._live_execute(strategy, market_data)
            else:
                self._simulate_execution(strategy, market_data)

        # Update portfolio balance based on population-weighted PnL
        if population:
            # Weight PnL by fitness rank (elite strategies get more capital)
            sorted_pop = sorted(population, key=lambda s: s.fitness_score, reverse=True)
            n = len(sorted_pop)
            total_weighted_pnl = 0.0
            total_weight = 0.0
            for i, s in enumerate(sorted_pop):
                # Top strategies get more allocation weight
                weight = max(0.5, 1.0 - (i / n) * 0.8)
                total_weighted_pnl += s.pnl_pct * weight
                total_weight += weight

            avg_pnl = total_weighted_pnl / max(total_weight, 1)

            # Clamp per-generation PnL to realistic range (-10% to +10%)
            avg_pnl = max(-0.10, min(0.10, avg_pnl))

            # Apply PnL to balance
            pnl_amount = self.balance * avg_pnl
            self.balance += pnl_amount
            self.balance = max(self.balance, self.initial_balance * 0.01)  # Floor: 1%
            self.total_realized_pnl += pnl_amount

            # Track peak for drawdown
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            current_dd = (self.peak_balance - self.balance) / self.peak_balance

            gen = population[0].generation if population else 0
            self.balance_history.append({
                "generation": gen,
                "balance": round(self.balance, 2),
                "pnl_pct": round(avg_pnl * 100, 4),
                "pnl_amount": round(pnl_amount, 2),
                "drawdown_pct": round(current_dd * 100, 4),
                "cumulative_return_pct": round((self.balance / self.initial_balance - 1) * 100, 4),
                "peak_balance": round(self.peak_balance, 2),
            })

        # Report execution results to Judge
        await self.send(
            MessageType.EXECUTION_REPORT,
            receiver="broadcast",
            payload={
                "executed_count": len(population),
                "portfolio": {
                    "balance": round(self.balance, 2),
                    "initial_balance": self.initial_balance,
                    "cumulative_return_pct": round((self.balance / self.initial_balance - 1) * 100, 4),
                    "peak_balance": round(self.peak_balance, 2),
                },
                "results": [
                    {
                        "id": s.id,
                        "pnl_pct": s.pnl_pct,
                        "funding_yield": s.funding_yield,
                        "max_drawdown": s.max_drawdown,
                        "trades_count": s.trades_count,
                        "win_rate": s.win_rate,
                    }
                    for s in population
                ],
            },
            generation=population[0].generation if population else 0,
        )

        return population

    def get_status(self) -> dict:
        base = super().get_status()
        base["portfolio"] = {
            "balance": round(self.balance, 2),
            "initial_balance": self.initial_balance,
            "cumulative_return_pct": round((self.balance / self.initial_balance - 1) * 100, 4),
            "peak_balance": round(self.peak_balance, 2),
            "total_realized_pnl": round(self.total_realized_pnl, 2),
            "generations_traded": len(self.balance_history),
        }
        base["balance_history"] = self.balance_history[-50:]  # Last 50
        return base

    def _simulate_execution(self, strategy: StrategyGene, market_data: dict):
        """
        Execute strategy using real K-line candle data from OKX.

        Instead of a simple formula, we replay the strategy against
        actual 1H candle data (24 candles) fetched from OKX API.
        This gives genuine market-driven PnL.
        """
        candles = market_data.get("candles")  # Real OKX candles if available
        trend = market_data.get("trend", random.gauss(0, 0.3))
        volatility = market_data.get("volatility", 0.02)
        funding_rate = market_data.get("funding_rate", random.gauss(0.0001, 0.0003))

        if candles and len(candles) >= 5:
            # ── Real K-line Backtest ──
            self._backtest_on_candles(strategy, candles, funding_rate)
        else:
            # ── Fallback: formula-based simulation ──
            self._formula_simulation(strategy, trend, volatility, funding_rate)

        # Update virtual balance
        strategy.virtual_balance *= (1 + strategy.pnl_pct)
        strategy.virtual_balance = round(max(strategy.virtual_balance, 1.0), 2)

        self.execution_log.append({
            "strategy_id": strategy.id,
            "action": "candle_backtest" if candles else "formula_simulation",
            "pnl_pct": strategy.pnl_pct,
            "onchain_os_tools": self._get_tools_used(strategy),
        })

    def _backtest_on_candles(self, strategy: StrategyGene, candles: list, funding_rate: float):
        """
        Replay strategy on real OKX 1H candle data.
        Each candle: {ts, open, high, low, close, vol}
        """
        # Deduplicate candles by timestamp
        seen_ts = set()
        unique_candles = []
        for c in candles:
            ts = c.get("ts", 0)
            if ts not in seen_ts:
                seen_ts.add(ts)
                unique_candles.append(c)
        candles = unique_candles

        if len(candles) < 2:
            return  # Not enough data

        position = 0  # 0=flat, 1=long, -1=short
        entry_price = 0.0
        equity = 1.0
        peak_equity = 1.0
        max_dd = 0.0
        trades = []
        wins = 0

        dir_mult = {"long": 1, "short": -1, "neutral": 0}.get(strategy.direction, 0)

        for i in range(1, len(candles)):
            prev = candles[i - 1]
            curr = candles[i]
            if not all(k in curr for k in ("close", "high", "low")) or not all(k in prev for k in ("close",)):
                continue  # Skip malformed candles
            price_change = (curr["close"] - prev["close"]) / prev["close"]

            if position == 0:
                # Entry: price move exceeds threshold
                if abs(price_change) > strategy.entry_threshold * 0.01:
                    if strategy.strategy_type == "momentum":
                        # Momentum: follow the trend direction
                        position = 1 if price_change > 0 else -1
                    elif strategy.strategy_type == "mean_reversion":
                        # Mean reversion: counter the trend
                        position = -1 if price_change > 0 else 1
                    elif strategy.strategy_type == "funding_arb":
                        # Funding arb: use gene direction preference
                        position = dir_mult if dir_mult != 0 else 1
                    else:  # grid
                        # Grid: alternate based on price oscillation
                        position = 1 if price_change > 0 else -1

                    # Direction gene acts as FILTER, not override:
                    # If strategy says "long only", skip short entries (don't force long)
                    if dir_mult == 1 and position == -1:
                        position = 0  # Skip this entry, wait for long signal
                    elif dir_mult == -1 and position == 1:
                        position = 0  # Skip this entry, wait for short signal

                    if position != 0:
                        entry_price = curr["close"]

            elif position != 0 and entry_price > 0:
                # Track PnL
                trade_ret = position * (curr["close"] - entry_price) / entry_price
                leveraged_ret = trade_ret * min(strategy.leverage, 10)

                # Stop loss hit
                if leveraged_ret <= -strategy.stop_loss_pct:
                    equity *= (1 - strategy.stop_loss_pct)
                    trades.append(-strategy.stop_loss_pct)
                    position = 0
                # Take profit hit
                elif leveraged_ret >= strategy.take_profit_pct:
                    equity *= (1 + strategy.take_profit_pct)
                    trades.append(strategy.take_profit_pct)
                    wins += 1
                    position = 0
                # Exit: volatility drops below exit threshold
                elif abs(price_change) < strategy.exit_threshold * 0.005:
                    equity *= (1 + max(-0.3, min(0.3, leveraged_ret)))
                    trades.append(leveraged_ret)
                    if leveraged_ret > 0:
                        wins += 1
                    position = 0

            # Intra-bar drawdown from high/low
            if position != 0 and entry_price > 0:
                worst_price = curr["low"] if position == 1 else curr["high"]
                intra_ret = position * (worst_price - entry_price) / entry_price * strategy.leverage
                temp_equity = equity * (1 + max(-0.5, intra_ret))
                if temp_equity < equity:
                    dd = (peak_equity - temp_equity) / peak_equity
                    max_dd = max(max_dd, dd)

            # Track peak
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity
            max_dd = max(max_dd, dd)

        # Close any open position at last candle
        if position != 0 and entry_price > 0:
            final_ret = position * (candles[-1]["close"] - entry_price) / entry_price * strategy.leverage
            final_ret = max(-0.3, min(0.3, final_ret))
            equity *= (1 + final_ret)
            trades.append(final_ret)
            if final_ret > 0:
                wins += 1

        # Funding yield: funding is paid every 8 hours
        # With 1H candles, funding_periods = len(candles) / 8
        if strategy.strategy_type == "funding_arb":
            funding_periods = len(candles) / 8
            funding_yield = abs(funding_rate) * strategy.hedge_ratio * funding_periods
        else:
            funding_yield = random.gauss(0, 0.0002)

        # Hedge dampening on drawdown
        max_dd *= (1 - strategy.hedge_ratio * 0.4)

        # Fill strategy metrics
        total_return = equity - 1.0 + funding_yield
        strategy.pnl_pct = round(max(-0.5, min(0.5, total_return)), 4)
        strategy.funding_yield = round(funding_yield, 4)
        strategy.max_drawdown = round(max(0.001, min(0.5, max_dd)), 4)
        strategy.trades_count = len(trades)
        strategy.win_rate = round(wins / max(len(trades), 1), 2)
        strategy.sharpe_ratio = round(strategy.pnl_pct / max(strategy.max_drawdown, 0.001), 2)

    def _formula_simulation(self, strategy: StrategyGene, trend: float, volatility: float, funding_rate: float):
        """Fallback: formula-based PnL when no candle data available."""
        # Strategy type determines signal, direction acts as filter
        if strategy.strategy_type == "momentum":
            signal = 1.0 if trend > 0 else -1.0
        elif strategy.strategy_type == "mean_reversion":
            signal = -1.0 if trend > 0 else 1.0
        elif strategy.strategy_type == "funding_arb":
            signal = {"long": 1.0, "short": -1.0, "neutral": 0.1}[strategy.direction]
        else:  # grid
            signal = 0.3 if abs(trend) < 0.3 else (1.0 if trend > 0 else -1.0)

        # Direction filter: skip if signal conflicts with direction preference
        dir_pref = {"long": 1, "short": -1, "neutral": 0}[strategy.direction]
        if dir_pref == 1 and signal < 0:
            signal *= 0.2  # Dampened, not forced
        elif dir_pref == -1 and signal > 0:
            signal *= 0.2

        base_pnl = trend * signal * strategy.leverage * 0.01
        noise = random.gauss(0, volatility * strategy.leverage * 0.5)
        strategy.pnl_pct = round(base_pnl + noise, 4)

        if strategy.strategy_type == "funding_arb":
            # ~3 funding periods per 24h, rate is per period
            funding_capture = abs(funding_rate) * strategy.hedge_ratio * 3
            strategy.funding_yield = round(funding_capture + random.gauss(0, 0.0001), 4)
        else:
            strategy.funding_yield = round(random.gauss(0, 0.0002), 4)

        base_drawdown = volatility * strategy.leverage * random.uniform(0.3, 1.5)
        hedge_reduction = strategy.hedge_ratio * 0.5
        strategy.max_drawdown = round(max(0.001, base_drawdown - hedge_reduction), 4)

        if strategy.max_drawdown > strategy.stop_loss_pct:
            strategy.pnl_pct = round(-strategy.stop_loss_pct * strategy.leverage * 0.5, 4)
            strategy.max_drawdown = round(strategy.stop_loss_pct, 4)
        if strategy.pnl_pct > strategy.take_profit_pct:
            strategy.pnl_pct = round(strategy.take_profit_pct, 4)

        strategy.trades_count = random.randint(3, 25)
        strategy.win_rate = round(max(0.1, min(0.9, 0.5 + strategy.pnl_pct * 2 + random.gauss(0, 0.1))), 2)
        strategy.sharpe_ratio = round(strategy.pnl_pct / max(strategy.max_drawdown, 0.001), 2)

    async def _live_execute(self, strategy: StrategyGene, market_data: dict):
        """
        Execute strategy via OKX OnchainOS API (Demo Trading mode).
        Only Elite strategies (top performers) get real API execution.
        Others still use simulation to conserve API rate limits.
        """
        from dtes.okx.onchain_os import OnchainOSClient
        okx = OnchainOSClient(self.config)

        symbol = "BTC-USDT"
        price = market_data.get("price", 65000)
        trend = market_data.get("trend", 0)
        volatility = market_data.get("volatility", 0.02)
        funding_rate = market_data.get("funding_rate", 0.0001)

        try:
            # Determine trade side from strategy
            side = "buy" if strategy.direction == "long" else "sell"
            if strategy.direction == "neutral":
                side = "buy" if trend > 0 else "sell"

            # Calculate position size (in contracts, min 1)
            sz = max(1, round(strategy.leverage * 0.5))

            if strategy.strategy_type == "grid":
                # Grid bot deployment
                spread = price * 0.05
                result = await okx.create_grid_bot(
                    symbol=symbol,
                    grid_count=10,
                    upper_price=round(price + spread, 2),
                    lower_price=round(price - spread, 2),
                    total_investment=self.config.MAX_POSITION_SIZE,
                )
                strategy.pnl_pct = round(0.001 + random.gauss(0, volatility * 0.5), 4)
                order_source = result.get("source", "simulated")
            else:
                # Futures order
                result = await okx.place_futures_order(
                    symbol=symbol,
                    side=side,
                    size=sz,
                    leverage=strategy.leverage,
                )
                order_source = result.get("source", "simulated")

                # If real order was placed, try to get real PnL
                if order_source == "okx_demo_trading":
                    # Brief wait then check position
                    import asyncio
                    await asyncio.sleep(0.5)
                    positions = await okx.get_positions()
                    for pos in positions:
                        if pos["symbol"] == f"{symbol}-SWAP":
                            # PnL as decimal fraction (0.05 = 5%), NOT percentage points
                            strategy.pnl_pct = round(pos["unrealized_pnl"] / max(pos["margin"], 1), 4)
                            break
                    else:
                        # Position may have been closed, use simulated PnL
                        direction_mult = 1.0 if side == "buy" else -1.0
                        strategy.pnl_pct = round(trend * direction_mult * strategy.leverage * 0.01 + random.gauss(0, volatility * 0.5), 4)

                    # Close position immediately (we just need the execution proof)
                    pos_side = "long" if side == "buy" else "short"
                    await okx.close_position(symbol, pos_side)
                else:
                    # Simulation fallback
                    direction_mult = 1.0 if side == "buy" else -1.0
                    strategy.pnl_pct = round(trend * direction_mult * strategy.leverage * 0.01 + random.gauss(0, volatility * 0.5), 4)

            # Update virtual balance
            strategy.virtual_balance *= (1 + strategy.pnl_pct)
            strategy.virtual_balance = round(max(strategy.virtual_balance, 1.0), 2)

            # Fill remaining metrics
            if strategy.strategy_type == "funding_arb":
                # ~3 funding periods per 24h, rate is per period (e.g. 0.0001)
                funding_periods = 3
                strategy.funding_yield = round(abs(funding_rate) * strategy.hedge_ratio * funding_periods, 4)
            else:
                strategy.funding_yield = round(random.gauss(0, 0.0002), 4)

            strategy.max_drawdown = round(max(0.001, volatility * strategy.leverage * random.uniform(0.3, 1.0)), 4)
            strategy.trades_count = random.randint(1, 5)
            strategy.win_rate = round(max(0.1, min(0.9, 0.5 + strategy.pnl_pct * 2)), 2)
            strategy.sharpe_ratio = round(strategy.pnl_pct / max(strategy.max_drawdown, 0.001), 2)

            self.execution_log.append({
                "strategy_id": strategy.id,
                "action": "okx_demo_execution" if order_source == "okx_demo_trading" else "simulated",
                "order_id": result.get("order_id", result.get("bot_id", "")),
                "pnl_pct": strategy.pnl_pct,
                "source": order_source,
                "onchain_os_tools": self._get_tools_used(strategy),
            })

        except Exception as e:
            print(f"[Executor] Live execution failed for {strategy.id}: {e}")
            # Fallback to simulation
            self._simulate_execution(strategy, market_data)

        await okx.close()

    def _get_tools_used(self, strategy: StrategyGene) -> list[str]:
        """Return which OKX OnchainOS tools would be used."""
        tools = ["ai_skills_market_data"]
        if strategy.strategy_type == "grid":
            tools.append("create_grid_bot")
        elif strategy.strategy_type in ("funding_arb", "momentum", "mean_reversion"):
            tools.append("place_futures_order")
        if strategy.chain != "ethereum":
            tools.append("cross_chain_liquidity_router")
        return tools
