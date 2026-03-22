"""GeneFi - Gene + DeFi Evolution Engine
Main FastAPI application with WebSocket real-time updates.
"""
import asyncio
import json
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from config import Config
from dtes.core.evolution import EvolutionEngine
from dtes.core.strategy import StrategyGene
from dtes.protocol.a2a import MessageBus, A2AMessage, MessageType
from dtes.agents.predictor import PredictorAgent
from dtes.agents.executor import ExecutorAgent
from dtes.agents.judge import JudgeAgent
from dtes.okx.onchain_os import OnchainOSClient
from dtes.core.backtest import run_monte_carlo_backtest, backtest_strategy, generate_multi_regime_series


# ─── Global State ─────────────────────────────────────────────
config = Config()
bus = MessageBus()
engine = EvolutionEngine(config)
okx_client = OnchainOSClient(config)

predictor = PredictorAgent(bus, config)
executor = ExecutorAgent(bus, config)
judge = JudgeAgent(bus, config)

# WebSocket connections
ws_clients = set()
evolution_task = None


async def broadcast_ws(event: str, data: dict):
    """Broadcast event to all WebSocket clients."""
    message = json.dumps({"event": event, "data": data, "timestamp": time.time()})
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_text(message)
        except Exception as e:
            print(f"[GeneFi] WS send error: {e}")
            dead.add(ws)
    for ws in dead:
        ws_clients.discard(ws)


# Register A2A bus listener for WebSocket forwarding
async def _a2a_to_ws(message: A2AMessage):
    await broadcast_ws("a2a_message", message.to_dict())

bus.subscribe_all(_a2a_to_ws)


# Register evolution engine events
async def _evolution_event(event_type: str, data: dict):
    await broadcast_ws(event_type, data)

engine.on_event(_evolution_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    os.makedirs(config.LOG_DIR, exist_ok=True)
    yield
    global evolution_task
    if evolution_task and not evolution_task.done():
        evolution_task.cancel()


app = FastAPI(
    title="GeneFi - Gene + DeFi Evolution Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ─── Pages ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve main dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r") as f:
        return HTMLResponse(content=f.read())


# ─── WebSocket ─────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        # Send current state on connect
        await ws.send_text(json.dumps({
            "event": "init",
            "data": {
                "population": [s.to_dict() for s in engine.population],
                "stats": engine.get_population_stats(),
                "history": [h.to_dict() for h in engine.history],
                "agents": {
                    "predictor": predictor.get_status(),
                    "executor": executor.get_status(),
                    "judge": judge.get_status(),
                },
                "config": {
                    "population_size": config.POPULATION_SIZE,
                    "mutation_rate": config.MUTATION_RATE,
                    "selection_pressure": config.SELECTION_PRESSURE,
                    "demo_mode": config.DEMO_MODE,
                    "execution_mode": config.EXECUTION_MODE,
                    "has_api_keys": config.has_api_keys,
                    "can_trade": config.can_trade,
                },
            },
            "timestamp": time.time(),
        }))

        while True:
            data = await ws.receive_text()
            print(f"[GeneFi] WS received: {data[:200]}")
            msg = json.loads(data)
            await handle_ws_command(ws, msg)

    except WebSocketDisconnect:
        print("[GeneFi] WS client disconnected")
        ws_clients.discard(ws)
    except Exception as e:
        print(f"[GeneFi] WS error: {e}")
        ws_clients.discard(ws)


async def handle_ws_command(ws: WebSocket, msg: dict):
    """Handle WebSocket commands from frontend."""
    cmd = msg.get("command")

    if cmd == "start_evolution":
        gens = msg.get("generations", config.MAX_GENERATIONS)
        await start_evolution(gens)
    elif cmd == "stop_evolution":
        await stop_evolution()
    elif cmd == "step_evolution":
        await step_evolution()
    elif cmd == "reset":
        await reset_evolution()
    elif cmd == "get_stats":
        await ws.send_text(json.dumps({
            "event": "stats",
            "data": engine.get_population_stats(),
            "timestamp": time.time(),
        }))
    elif cmd == "get_market":
        market = await okx_client.get_market_data()
        await ws.send_text(json.dumps({
            "event": "market_data",
            "data": market,
            "timestamp": time.time(),
        }))
    elif cmd == "update_config":
        # Dynamic config update from settings panel
        params = msg.get("params", {})
        if "population_size" in params:
            config.POPULATION_SIZE = max(5, min(100, int(params["population_size"])))
        if "mutation_rate" in params:
            config.MUTATION_RATE = max(0.01, min(0.5, float(params["mutation_rate"])))
        if "selection_pressure" in params:
            config.SELECTION_PRESSURE = max(0.1, min(0.6, float(params["selection_pressure"])))
        if "max_generations" in params:
            config.MAX_GENERATIONS = max(1, min(200, int(params["max_generations"])))
        await broadcast_ws("config_updated", {
            "population_size": config.POPULATION_SIZE,
            "mutation_rate": config.MUTATION_RATE,
            "selection_pressure": config.SELECTION_PRESSURE,
            "max_generations": config.MAX_GENERATIONS,
        })
    elif cmd == "export_strategies":
        # Export top strategies
        top_n = msg.get("top_n", 5)
        sorted_pop = sorted(engine.population, key=lambda s: s.fitness_score, reverse=True)
        export = {
            "exported_at": time.time(),
            "generation": engine.generation,
            "total_generations_run": len(engine.history),
            "strategies": [s.to_dict() for s in sorted_pop[:top_n]],
            "evolution_config": {
                "population_size": config.POPULATION_SIZE,
                "mutation_rate": config.MUTATION_RATE,
                "selection_pressure": config.SELECTION_PRESSURE,
                "fitness_weights": {
                    "pnl": config.PNL_WEIGHT,
                    "funding": config.FUNDING_WEIGHT,
                    "drawdown": config.DRAWDOWN_WEIGHT,
                },
            },
        }
        await ws.send_text(json.dumps({
            "event": "export_result",
            "data": export,
            "timestamp": time.time(),
        }))
    elif cmd == "switch_mode":
        mode = msg.get("mode", "simulation")
        if mode in ("simulation", "demo_api"):
            config.EXECUTION_MODE = mode
            await broadcast_ws("mode_changed", {
                "execution_mode": config.EXECUTION_MODE,
                "has_api_keys": config.has_api_keys,
                "can_trade": config.can_trade,
            })
            print(f"[GeneFi] Execution mode changed to: {mode}")
    elif cmd == "deploy_strategy":
        # Deploy the best evolved strategy to OKX
        result = await deploy_best_strategy(msg.get("strategy_id"))
        await ws.send_text(json.dumps({
            "event": "deploy_result",
            "data": result,
            "timestamp": time.time(),
        }))
    elif cmd == "get_gene_drift":
        # Return gene drift data across generations
        await ws.send_text(json.dumps({
            "event": "gene_drift_data",
            "data": get_gene_drift_data(),
            "timestamp": time.time(),
        }))


# ─── Evolution Control ─────────────────────────────────────────

async def run_evolution_loop(generations: int):
    """Run the full evolution loop."""
    global evolution_task

    try:
        # Initialize population
        _all_candles = None  # Will be fetched on first generation
        engine.initialize_population()
        print(f"[GeneFi] Population initialized: {len(engine.population)} strategies")
        await broadcast_ws("population_initialized", {
            "population": [s.to_dict() for s in engine.population],
            "stats": engine.get_population_stats(),
        })

        for gen in range(generations):
            if evolution_task and evolution_task.cancelled():
                break

            # Get market data from OnchainOS (including real K-line candles)
            market_data = await okx_client.get_market_data()
            funding = await okx_client.get_funding_rate()
            liquidity = await okx_client.get_cross_chain_liquidity()

            # Fetch extended candle history (7 days) on first gen, then use sliding window
            if gen == 0:
                _all_candles = await okx_client.get_candles("BTC-USDT", "1H", 100)

            market_data["funding_detail"] = funding
            market_data["cross_chain"] = liquidity

            # Sliding window: each generation gets a DIFFERENT slice of candles
            # Step = (total - window) / generations, so windows don't overlap much
            if _all_candles and len(_all_candles) > 20:
                window_size = min(24, len(_all_candles) // 2)
                usable = len(_all_candles) - window_size
                step = max(1, usable // max(generations, 1))
                start_idx = min(gen * step, usable)
                end_idx = start_idx + window_size
                market_data["candles"] = _all_candles[start_idx:end_idx]
                print(f"[GeneFi] Gen {gen}: candles [{start_idx}:{end_idx}] of {len(_all_candles)}")
            elif _all_candles:
                market_data["candles"] = _all_candles

            await broadcast_ws("market_data", market_data)

            # Run one generation
            print(f"[GeneFi] Running generation {gen}...")
            snapshot = await engine.run_generation(
                predictor_fn=predictor.generate_population,
                executor_fn=executor.execute_strategies,
                judge_fn=judge.evaluate_population,
                market_data=market_data,
            )
            print(f"[GeneFi] Gen {gen}: avg={snapshot.avg_fitness:.4f} best={snapshot.best_fitness:.4f}")

            # Record gene drift
            record_gene_drift(engine.population, engine.generation)

            # Broadcast results
            await broadcast_ws("generation_result", {
                "snapshot": snapshot.to_dict(),
                "population": [s.to_dict() for s in engine.population],
                "stats": engine.get_population_stats(),
                "agents": {
                    "predictor": predictor.get_status(),
                    "executor": executor.get_status(),
                    "judge": judge.get_status(),
                },
                "gene_drift": _gene_drift_history[-1] if _gene_drift_history else None,
            })

            # Pace the evolution (allow UI to update)
            await asyncio.sleep(1.5)

        # Generate evolution report with baseline comparison
        report = await _generate_evolution_report()

        await broadcast_ws("evolution_complete", {
            "total_generations": engine.generation,
            "final_stats": engine.get_population_stats(),
            "history": [h.to_dict() for h in engine.history],
            "report": report,
        })
    except Exception as e:
        import traceback
        print(f"[GeneFi ERROR] Evolution loop failed: {e}")
        traceback.print_exc()


async def _generate_evolution_report() -> dict:
    """Generate a comprehensive evolution report with baseline comparison."""
    if not engine.history:
        return {}

    # Evolved performance
    evolved_avg = [h.avg_fitness for h in engine.history]
    evolved_best = [h.best_fitness for h in engine.history]

    # Quick random baseline (3 rounds averaged)
    baseline_scores = []
    for _ in range(3):
        random_pop = [StrategyGene.random() for _ in range(config.POPULATION_SIZE)]
        market = await okx_client.get_market_data()
        simulated = await executor.execute_strategies(random_pop, market)
        for s in simulated:
            from dtes.core.fitness import calculate_fitness
            r = calculate_fitness(s.pnl_pct, s.funding_yield, s.max_drawdown)
            s.fitness_score = r.score
        avg = sum(s.fitness_score for s in simulated) / len(simulated)
        baseline_scores.append(avg)
    baseline_avg = sum(baseline_scores) / len(baseline_scores)

    # Top strategies
    sorted_pop = sorted(engine.population, key=lambda s: s.fitness_score, reverse=True)
    top5 = [s.to_dict() for s in sorted_pop[:5]]

    # API call stats from executor log
    api_calls = len([l for l in executor.execution_log if l.get("source") == "okx_demo_trading"])
    sim_calls = len([l for l in executor.execution_log if l.get("source") != "okx_demo_trading"])

    # OKX tools used
    tools_used = set()
    for log in executor.execution_log:
        for tool in log.get("onchain_os_tools", []):
            tools_used.add(tool)

    improvement = evolved_avg[-1] - baseline_avg if evolved_avg else 0

    # Monte Carlo statistical validation
    print("[GeneFi] Running Monte Carlo backtest (30 trials)...")
    top_strategies = sorted_pop[:min(10, len(sorted_pop))]
    mc_result = run_monte_carlo_backtest(top_strategies, n_trials=30, n_steps=500)
    print(f"[GeneFi] MC Result: alpha={mc_result.alpha:.4f} p={mc_result.p_value:.6f} sig={mc_result.is_significant}")

    return {
        "generations_run": len(engine.history),
        "final_avg_fitness": round(evolved_avg[-1], 6) if evolved_avg else 0,
        "final_best_fitness": round(evolved_best[-1], 6) if evolved_best else 0,
        "random_baseline_avg": round(baseline_avg, 6),
        "improvement_over_random": round(improvement, 6),
        "improvement_pct": round(improvement / max(abs(baseline_avg), 0.0001) * 100, 1),
        "top5_strategies": top5,
        "total_trades_executed": sum(s.trades_count for s in engine.population),
        "api_calls_real": api_calls,
        "api_calls_simulated": sim_calls,
        "okx_tools_used": sorted(list(tools_used)),
        "execution_mode": config.EXECUTION_MODE,
        "market_source": "mcp_agent_trade_kit" if okx_client._mcp_available else ("okx_live" if okx_client._real_api_available else "simulated"),
        "monte_carlo": mc_result.to_dict(),
        "mcp_stats": okx_client.get_mcp_stats(),
    }


async def deploy_best_strategy(strategy_id: str = None) -> dict:
    """Deploy the best evolved strategy to OKX (Demo Trading)."""
    if not engine.population:
        return {"status": "error", "message": "No strategies to deploy. Run evolution first."}

    # Find strategy
    if strategy_id:
        target = next((s for s in engine.population if s.id == strategy_id), None)
    else:
        target = max(engine.population, key=lambda s: s.fitness_score)

    if not target:
        return {"status": "error", "message": "Strategy not found."}

    results = {"strategy": target.to_dict(), "actions": [], "status": "deployed"}

    # Execute based on strategy type
    if target.strategy_type == "grid":
        # Deploy grid bot
        market = await okx_client.get_market_data()
        price = market.get("price", 65000)
        upper = price * (1 + target.entry_threshold)
        lower = price * (1 - target.entry_threshold)
        r = await okx_client.create_grid_bot(
            symbol="BTC-USDT",
            grid_count=10,
            upper_price=round(upper, 2),
            lower_price=round(lower, 2),
            total_investment=min(config.MAX_POSITION_SIZE, 100),
        )
        results["actions"].append({"type": "grid_bot", "result": r})
    elif target.strategy_type == "funding_arb":
        # Open hedge position for funding arbitrage
        side = "buy" if target.direction == "long" else "sell"
        r = await okx_client.place_futures_order(
            symbol="BTC-USDT",
            side=side,
            size=min(config.MAX_POSITION_SIZE / 65000, 0.01),
            leverage=min(target.leverage, config.MAX_LEVERAGE_LIMIT),
        )
        results["actions"].append({"type": "futures_order", "result": r})
    else:
        # Momentum / mean reversion: place directional trade
        side = "buy" if target.direction == "long" else "sell"
        r = await okx_client.place_futures_order(
            symbol="BTC-USDT",
            side=side,
            size=min(config.MAX_POSITION_SIZE / 65000, 0.01),
            leverage=min(target.leverage, config.MAX_LEVERAGE_LIMIT),
        )
        results["actions"].append({"type": "futures_order", "result": r})

    # If safe mode was triggered, also deploy to Earn
    if judge.safe_mode_active:
        earn_r = await okx_client.switch_to_earn(
            amount=config.MAX_POSITION_SIZE * target.hedge_ratio
        )
        results["actions"].append({"type": "earn_deposit", "result": earn_r})

    # Log API sources
    results["api_sources"] = list(set(
        a["result"].get("source", "unknown") for a in results["actions"]
    ))

    print(f"[GeneFi] Strategy deployed: {target.id} type={target.strategy_type} actions={len(results['actions'])}")
    return results


# ─── Gene Drift Tracking ─────────────────────────────────────

_gene_drift_history = []  # Track gene averages per generation

def record_gene_drift(population, generation: int):
    """Record population gene averages for drift analysis."""
    if not population:
        return
    n = len(population)
    drift = {
        "generation": generation,
        "leverage": round(sum(s.leverage for s in population) / n, 3),
        "entry_threshold": round(sum(s.entry_threshold for s in population) / n, 4),
        "exit_threshold": round(sum(s.exit_threshold for s in population) / n, 4),
        "hedge_ratio": round(sum(s.hedge_ratio for s in population) / n, 3),
        "stop_loss_pct": round(sum(s.stop_loss_pct for s in population) / n, 4),
        "take_profit_pct": round(sum(s.take_profit_pct for s in population) / n, 4),
        "direction_dist": {
            "long": sum(1 for s in population if s.direction == "long") / n,
            "short": sum(1 for s in population if s.direction == "short") / n,
            "neutral": sum(1 for s in population if s.direction == "neutral") / n,
        },
        "type_dist": {
            "funding_arb": sum(1 for s in population if s.strategy_type == "funding_arb") / n,
            "grid": sum(1 for s in population if s.strategy_type == "grid") / n,
            "momentum": sum(1 for s in population if s.strategy_type == "momentum") / n,
            "mean_reversion": sum(1 for s in population if s.strategy_type == "mean_reversion") / n,
        },
    }
    _gene_drift_history.append(drift)


def get_gene_drift_data() -> dict:
    """Get gene drift data for visualization."""
    return {
        "generations": len(_gene_drift_history),
        "drift": _gene_drift_history,
    }


async def start_evolution(generations: int = 10):
    global evolution_task
    if evolution_task and not evolution_task.done():
        return
    evolution_task = asyncio.create_task(run_evolution_loop(generations))


async def stop_evolution():
    global evolution_task
    if evolution_task and not evolution_task.done():
        evolution_task.cancel()
        await broadcast_ws("evolution_stopped", {"generation": engine.generation})


async def step_evolution():
    """Run a single evolution step."""
    if not engine.population:
        engine.initialize_population()
        await broadcast_ws("population_initialized", {
            "population": [s.to_dict() for s in engine.population],
        })

    market_data = await okx_client.get_market_data()
    snapshot = await engine.run_generation(
        predictor_fn=predictor.generate_population,
        executor_fn=executor.execute_strategies,
        judge_fn=judge.evaluate_population,
        market_data=market_data,
    )
    await broadcast_ws("generation_result", {
        "snapshot": snapshot.to_dict(),
        "population": [s.to_dict() for s in engine.population],
        "stats": engine.get_population_stats(),
    })


async def reset_evolution():
    global evolution_task
    if evolution_task and not evolution_task.done():
        evolution_task.cancel()
    engine.population = []
    engine.generation = 0
    engine.history = []
    judge.fitness_history = []
    judge.safe_mode_active = False
    judge.consecutive_declines = 0
    executor.balance = executor.initial_balance
    executor.peak_balance = executor.initial_balance
    executor.balance_history = []
    executor.total_realized_pnl = 0.0
    _gene_drift_history.clear()
    await broadcast_ws("reset", {"status": "ok"})


# ─── REST API ──────────────────────────────────────────────────

@app.get("/api/account")
async def api_account():
    """OKX account info (balance + positions)."""
    balance = await okx_client.get_balance()
    positions = await okx_client.get_positions()
    return {
        "balance": balance,
        "positions": positions,
        "execution_mode": config.EXECUTION_MODE,
        "has_api_keys": config.has_api_keys,
        "can_trade": config.can_trade,
    }


@app.get("/api/status")
async def api_status():
    return {
        "status": "running",
        "version": "1.0.0",
        "demo_mode": config.DEMO_MODE,
        "execution_mode": config.EXECUTION_MODE,
        "evolution": engine.get_population_stats(),
        "agents": {
            "predictor": predictor.get_status(),
            "executor": executor.get_status(),
            "judge": judge.get_status(),
        },
        "mcp": okx_client.get_mcp_stats(),
    }


@app.get("/api/population")
async def api_population():
    return {
        "population": [s.to_dict() for s in engine.population],
        "stats": engine.get_population_stats(),
    }


@app.get("/api/history")
async def api_history():
    return {
        "history": [h.to_dict() for h in engine.history],
    }


@app.get("/api/messages")
async def api_messages(limit: int = 50):
    return {
        "messages": [m.to_dict() for m in bus.get_messages(limit=limit)],
    }


@app.get("/api/market")
async def api_market():
    market = await okx_client.get_market_data()
    funding = await okx_client.get_funding_rate()
    liquidity = await okx_client.get_cross_chain_liquidity()
    return {
        "market": market,
        "funding": funding,
        "liquidity": liquidity,
    }


@app.get("/api/export")
async def api_export(top_n: int = 5):
    """Export top-performing strategies as JSON."""
    sorted_pop = sorted(engine.population, key=lambda s: s.fitness_score, reverse=True)
    return {
        "exported_at": time.time(),
        "generation": engine.generation,
        "total_generations_run": len(engine.history),
        "strategies": [s.to_dict() for s in sorted_pop[:top_n]],
        "fitness_timeline": [
            {"gen": h.generation, "avg": h.avg_fitness, "best": h.best_fitness, "worst": h.worst_fitness}
            for h in engine.history
        ],
    }


@app.get("/api/backtest")
async def api_backtest():
    """Compare evolved strategies vs random baseline."""
    if not engine.history:
        return {"error": "No evolution history. Run evolution first."}

    # Evolved performance (from actual runs)
    evolved_best = [h.best_fitness for h in engine.history]
    evolved_avg = [h.avg_fitness for h in engine.history]

    # Generate random baseline for comparison
    import random as rng
    baseline_avg = []
    baseline_best = []
    for _ in range(len(engine.history)):
        random_pop = [StrategyGene.random() for _ in range(config.POPULATION_SIZE)]
        # Quick simulate
        market = await okx_client.get_market_data()
        simulated = await executor.execute_strategies(random_pop, market)
        for s in simulated:
            from dtes.core.fitness import calculate_fitness
            r = calculate_fitness(s.pnl_pct, s.funding_yield, s.max_drawdown)
            s.fitness_score = r.score
        scores = [s.fitness_score for s in simulated]
        baseline_avg.append(round(sum(scores) / len(scores), 6))
        baseline_best.append(round(max(scores), 6))

    return {
        "generations": len(engine.history),
        "evolved": {"avg": evolved_avg, "best": evolved_best},
        "random_baseline": {"avg": baseline_avg, "best": baseline_best},
        "improvement": {
            "avg_fitness_gain": round(evolved_avg[-1] - baseline_avg[-1], 6) if evolved_avg else 0,
            "best_fitness_gain": round(evolved_best[-1] - baseline_best[-1], 6) if evolved_best else 0,
        },
    }


@app.get("/api/simulate_investment")
async def api_simulate_investment(capital: float = 10000, days: int = 7):
    """
    Investment Simulator: Show users how evolved strategies would perform
    with their capital on real OKX historical data.
    """
    if not engine.population:
        return {"error": "请先运行进化 Run evolution first"}

    # Get top 5 evolved strategies
    sorted_pop = sorted(engine.population, key=lambda s: s.fitness_score, reverse=True)
    top5 = sorted_pop[:5]

    # Fetch longer K-line history from OKX (1H candles, up to 7 days = 168 candles)
    hours = min(days * 24, 168)
    candles = await okx_client.get_candles("BTC-USDT", "1H", hours)
    if not candles or len(candles) < 10:
        return {"error": "无法获取K线数据 Cannot fetch candle data"}

    # Run backtest for each top strategy
    from dtes.core.backtest import backtest_strategy
    results = []
    for strat in top5:
        prices = [c["close"] for c in candles]
        funding_rates = [0.0001] * len(candles)  # Approx
        bt = backtest_strategy(strat, prices, funding_rates)
        results.append({
            "strategy": strat.to_dict(),
            "backtest": bt.to_dict(),
            "equity_curve": bt.cumulative_pnl,
        })

    # Portfolio: equal-weight blend of top 5
    n_points = len(results[0]["equity_curve"]) if results else 0
    portfolio_curve = []
    for i in range(n_points):
        avg_pnl = sum(r["equity_curve"][i] for r in results) / len(results)
        portfolio_curve.append(round(avg_pnl, 6))

    # Apply capital
    capital_curve = [round(capital * (1 + p), 2) for p in portfolio_curve]
    final_capital = capital_curve[-1] if capital_curve else capital
    total_return = (final_capital / capital - 1)
    max_capital = max(capital_curve) if capital_curve else capital
    min_capital = min(capital_curve) if capital_curve else capital

    # Random baseline for comparison
    random_pop = [StrategyGene.random() for _ in range(5)]
    random_results = []
    for strat in random_pop:
        prices = [c["close"] for c in candles]
        bt = backtest_strategy(strat, prices)
        random_results.append(bt)
    random_avg_return = sum(r.total_return for r in random_results) / len(random_results)
    random_final = round(capital * (1 + random_avg_return), 2)

    # Candle time range
    start_time = candles[0]["ts"]
    end_time = candles[-1]["ts"]

    return {
        "input": {"capital": capital, "days": days},
        "period": {
            "start_ts": start_time,
            "end_ts": end_time,
            "candles_count": len(candles),
            "hours": len(candles),
        },
        "evolved_portfolio": {
            "final_capital": final_capital,
            "total_return_pct": round(total_return * 100, 2),
            "max_capital": max_capital,
            "min_capital": min_capital,
            "max_drawdown_pct": round((max_capital - min_capital) / max_capital * 100, 2),
            "capital_curve": capital_curve,
        },
        "random_baseline": {
            "final_capital": random_final,
            "total_return_pct": round(random_avg_return * 100, 2),
        },
        "alpha": {
            "evolved_vs_random": round((total_return - random_avg_return) * 100, 2),
            "extra_profit": round(final_capital - random_final, 2),
        },
        "strategies": results,
        "btc_price": {
            "start": candles[0]["close"],
            "end": candles[-1]["close"],
            "change_pct": round((candles[-1]["close"] / candles[0]["close"] - 1) * 100, 2),
        },
    }


@app.get("/api/dex_quote")
async def api_dex_quote(chain: str = "ethereum", amount: float = 1000):
    """Get DEX swap quote via OnchainOS aggregator (500+ DEX)."""
    if okx_client._dex:
        quote = await okx_client._dex.get_quote(chain, "USDT", "WETH", amount)
        best_chain = await okx_client._dex.find_best_chain("WETH", amount)
        return {
            "quote": quote.to_dict(),
            "best_chain": best_chain,
            "dex_stats": okx_client._dex.get_stats(),
        }
    return {"error": "DEX aggregator not available"}


@app.get("/api/monte_carlo")
async def api_monte_carlo(n_trials: int = 30):
    """Run Monte Carlo statistical validation on evolved strategies."""
    if not engine.population:
        return {"error": "No strategies. Run evolution first."}

    sorted_pop = sorted(engine.population, key=lambda s: s.fitness_score, reverse=True)
    top = sorted_pop[:min(10, len(sorted_pop))]
    result = run_monte_carlo_backtest(top, n_trials=n_trials, n_steps=500)
    return result.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
