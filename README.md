# GeneFi - 基因金融 | Gene + DeFi Evolution Engine

<div align="center">

**用遗传进化算法驱动 DeFi 交易策略自适应优化的多智能体系统**

*A multi-agent system powered by genetic evolution for adaptive DeFi trading strategy optimization*

[![OKX Agent Trade Kit](https://img.shields.io/badge/OKX-Agent_Trade_Kit-00DC82?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=)](https://www.okx.com/zh-hans/agent-tradekit)
[![MCP Tools](https://img.shields.io/badge/MCP_Tools-119-blue?style=for-the-badge)](https://github.com/okx/agent-trade-kit)
[![OnchainOS](https://img.shields.io/badge/OnchainOS-500+_DEX-cyan?style=for-the-badge)](https://web3.okx.com/zh-hans/onchainos)
[![Skills](https://img.shields.io/badge/AI_Skills-11-purple?style=for-the-badge)](https://github.com/okx/onchainos-skills)

</div>

---

## What is GeneFi?

GeneFi 将每套交易策略视为**生物个体**，通过遗传变异、交叉互换和自然选择，让策略种群在真实市场中自动进化。

| Biology | GeneFi |
|---|---|
| DNA | Strategy Parameters (leverage, direction, hedge...) |
| Individual | A Complete Trading Strategy |
| Population | All Current Strategies |
| Fitness | Profitability Score |
| Natural Selection | Eliminate Underperformers |
| Mutation | Parameter Tweaks for Offspring |
| Crossover | Gene Combination from Elite Parents |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GeneFi Evolution Engine                       │
│                                                                 │
│   ┌─────────────┐   A2A    ┌─────────────┐   A2A    ┌─────────────┐
│   │  Predictor   │────────>│  Executor    │────────>│    Judge     │
│   │  预测者       │<────────│  执行者       │<────────│    裁判者     │
│   │  Claude Opus │         │  OnchainOS   │         │ Claude Sonnet│
│   └──────┬──────┘         └──────┬──────┘         └──────┬──────┘
│          │                       │                        │
│          │    ┌──────────────────┼────────────────────────┘
│          │    │                  │
│          ▼    ▼                  ▼
│   ┌─────────────────────────────────────────────┐
│   │         OKX Agent Trade Kit (MCP)            │
│   │                                              │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│   │  │ Market    │ │ Swap     │ │ Account  │    │
│   │  │ 13 tools  │ │ 17 tools │ │ 13 tools │    │
│   │  └──────────┘ └──────────┘ └──────────┘    │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│   │  │ Spot     │ │ Option   │ │ Grid     │    │
│   │  │ 13 tools │ │ 14 tools │ │ 5 tools  │    │
│   │  └──────────┘ └──────────┘ └──────────┘    │
│   │                                              │
│   │  Total: 119 MCP Tools via stdio protocol     │
│   └─────────────────────────────────────────────┘
│                         │
│                         ▼
│   ┌─────────────────────────────────────────────┐
│   │           OnchainOS Ecosystem                │
│   │                                              │
│   │  DEX Aggregator    │ 500+ DEX, 20+ Chains   │
│   │  AI Skills (11)    │ Wallet, Security, x402  │
│   │  Earn API          │ Safe Mode Auto-Switch   │
│   └─────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

---

## Evolution Flow

```
 ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
 │ 1. 检测  │───>│ 2. 生成  │───>│ 3. 回测  │───>│ 4. 评分  │───>│ 5. 进化  │
 │ Detect   │    │ Generate │    │ Backtest │    │ Score    │    │ Evolve   │
 │ Regime   │    │ Pop      │    │ Candles  │    │ Fitness  │    │ Select   │
 └─────────┘    └─────────┘    └─────────┘    └─────────┘    └────┬────┘
      ▲                                                            │
      └────────────────────── Next Generation ─────────────────────┘

Fitness = 0.5 × PnL% + 0.3 × FundingYield × 50 − 0.2 × MaxDrawdown

Population: Elite (Top 20%) → Survive (Mid 50%) → Eliminate (Bottom 30%)
```

---

## OKX Integration Map

```
┌──────────────────────────────────────────────────────────────┐
│                   GeneFi × OKX Integration                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ Agent Trade Kit (MCP) ─────────────────────────────────┐ │
│  │  Priority 1: MCP stdio protocol (119 tools)              │ │
│  │  • market_get_ticker      → Real-time BTC/ETH price      │ │
│  │  • market_get_funding_rate → Funding rate detection       │ │
│  │  • swap_place_order       → Futures order execution       │ │
│  │  • swap_close_position    → Position management           │ │
│  │  • swap_set_leverage      → Risk control                  │ │
│  │  • account_get_balance    → Portfolio tracking             │ │
│  │  • grid_create_order      → Grid bot deployment           │ │
│  │  • spot_place_order       → Spot trading                  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ OnchainOS DEX Aggregator ──────────────────────────────┐ │
│  │  • 500+ DEX liquidity sources                            │ │
│  │  • 20+ chains (ETH, ARB, OP, MATIC, BASE, BSC...)       │ │
│  │  • Smart order splitting for optimal routing              │ │
│  │  • Cross-chain swap support                               │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ OnchainOS AI Skills (11 installed) ────────────────────┐ │
│  │  okx-agentic-wallet  │ okx-dex-swap    │ okx-security   │ │
│  │  okx-dex-market      │ okx-dex-token   │ okx-audit-log  │ │
│  │  okx-dex-signal      │ okx-dex-trenches│ okx-x402-payment│ │
│  │  okx-onchain-gateway │ okx-wallet-portfolio              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ OKX Earn (Safe Mode) ──────────────────────────────────┐ │
│  │  Auto-switch when population fitness declines 3+ gens    │ │
│  │  POST /api/v5/finance/savings/purchase-redempt            │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  Data Flow Priority: MCP → REST API → Simulation             │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---|---|
| **Genetic Evolution Engine** | 9-gene strategy model with mutation, crossover, and natural selection |
| **3-Agent A2A Protocol** | Predictor → Executor → Judge closed-loop with audit logging |
| **119 MCP Tools** | Full OKX Agent Trade Kit integration via MCP stdio |
| **Real OKX Market Data** | Live BTC/ETH prices, funding rates, orderbook depth |
| **Demo Trading Execution** | Real order placement on OKX Demo Trading (with orderId proof) |
| **8 Market Regime Detection** | Bull/bear volatile, trending, range-bound, funding extreme |
| **Investment Simulator** | Input capital → backtest on real OKX K-line → equity curve |
| **Monte Carlo Validation** | Multi-regime statistical test proving evolution generates alpha |
| **Safe Mode → OKX Earn** | Auto-switch to stable yield when fitness declines |
| **One-Click Deploy** | Deploy best evolved strategy directly to OKX |
| **Gene Drift Visualization** | Track how parameters evolve across generations |
| **Force-Directed Graph** | SVG physics simulation showing strategy ecosystem |
| **Strategy Export** | Download/copy top strategies as JSON config |
| **500+ DEX Aggregation** | OnchainOS cross-chain optimal routing |
| **11 AI Skills** | Installed OnchainOS skills for wallet, security, payments |

---

## Quick Start

### Local Development

```bash
# 1. Clone
git clone https://github.com/Brian5216/GeneFi.git
cd GeneFi

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Node dependencies
npm install

# 4. (Optional) Configure OKX Demo Trading
cp .env.example .env
# Edit .env with your OKX API keys

# 5. Start backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 \
  --loop asyncio --http h11 --ws websockets &

# 6. Start frontend proxy
node serve.js

# 7. Open http://localhost:8000
```

### Docker

```bash
docker-compose up --build
# Open http://localhost:8000
```

### OKX Agent Trade Kit MCP Setup

```bash
# Install MCP server
npm install -g okx-trade-mcp

# Configure credentials
mkdir -p ~/.okx
cat > ~/.okx/config.toml << EOF
default_profile = "demo"

[profiles.demo]
api_key = "your-api-key"
secret_key = "your-secret-key"
passphrase = "your-passphrase"
demo = true
EOF

# Install OnchainOS Skills
npx skills add okx/onchainos-skills --yes
```

---

## Strategy Gene Model

Each trading strategy is encoded as a **9-gene chromosome**:

```
┌─────────────────────────────────────────────────────────┐
│                  Strategy Gene Model                     │
├────────────────┬──────────┬─────────────────────────────┤
│ Gene           │ Range    │ Description                  │
├────────────────┼──────────┼─────────────────────────────┤
│ leverage       │ 1-20x    │ Position leverage            │
│ entry_threshold│ 0.1-0.95 │ Entry signal sensitivity     │
│ exit_threshold │ 0.05-0.6 │ Exit trigger level           │
│ hedge_ratio    │ 0-1.0    │ Hedging proportion           │
│ stop_loss_pct  │ 2-15%    │ Stop loss percentage         │
│ take_profit_pct│ 5-30%    │ Take profit percentage       │
│ direction      │ L/S/N    │ Long, Short, or Neutral      │
│ chain          │ 6 chains │ ETH, ARB, OP, MATIC, BASE...│
│ strategy_type  │ 4 types  │ Arb, Grid, Momentum, MR     │
└────────────────┴──────────┴─────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Frontend | Vanilla JS + SVG + Canvas |
| Communication | WebSocket + A2A JSON Protocol |
| Proxy | Node.js HTTP/WS Reverse Proxy |
| AI Models | Claude Opus + Claude Sonnet |
| Trading (MCP) | OKX Agent Trade Kit (119 tools) |
| DeFi | OnchainOS DEX Aggregator (500+ DEX) |
| Deployment | Docker multi-stage build |

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Main dashboard |
| `/ws` | WS | WebSocket real-time updates |
| `/api/status` | GET | System status + MCP stats |
| `/api/market` | GET | Live market data (MCP source) |
| `/api/account` | GET | OKX account balance & positions |
| `/api/population` | GET | Current strategy population |
| `/api/history` | GET | Evolution history |
| `/api/export` | GET | Export top strategies (JSON) |
| `/api/backtest` | GET | Evolved vs random comparison |
| `/api/dex_quote` | GET | DEX swap quote (500+ DEX) |
| `/api/simulate_investment` | GET | Investment simulator |
| `/api/monte_carlo` | GET | Statistical validation |

---

## Project Structure

```
GeneFi/
├── main.py                     # FastAPI app + WebSocket + evolution loop
├── config.py                   # Configuration management
├── serve.js                    # Node.js reverse proxy (static + WS + API)
├── mcp_proxy.js                # MCP proxy with undici ProxyAgent support
├── dtes/
│   ├── core/
│   │   ├── strategy.py         # 9-gene strategy model
│   │   ├── fitness.py          # Fitness scoring function
│   │   ├── evolution.py        # Evolution engine (mutation/crossover/selection)
│   │   └── backtest.py         # Monte Carlo multi-regime backtester
│   ├── agents/
│   │   ├── base.py             # Base agent class
│   │   ├── predictor.py        # Predictor (population incubator)
│   │   ├── executor.py         # Executor (strategy execution + OKX trading)
│   │   └── judge.py            # Judge (fitness evaluation + safe mode)
│   ├── protocol/
│   │   └── a2a.py              # A2A communication protocol + audit log
│   └── okx/
│       ├── onchain_os.py       # OKX OnchainOS integration (MCP priority)
│       ├── mcp_bridge.py       # Python → MCP stdio bridge
│       └── dex_aggregator.py   # DEX aggregation (500+ DEX, 20+ chains)
├── static/
│   ├── index.html              # Dashboard (4-tab layout)
│   ├── css/style.css           # Dark theme + responsive design
│   └── js/
│       ├── evolution-viz.js    # Force-directed graph visualization
│       └── app.js              # WebSocket client + UI state management
├── .agents/skills/             # 11 OnchainOS AI Skills
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Container orchestration
├── .env.example                # Environment variables template
└── PROGRESS.md                 # Project progress tracker
```

---

## License

MIT

---

<div align="center">

Built for **OKX AI Hackathon Season 2** with Claude + OKX Agent Trade Kit

</div>
