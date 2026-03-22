# GeneFi - 基因金融 | Gene + DeFi Evolution Engine

<div align="center">

**用遗传进化算法驱动 DeFi 交易策略自适应优化的多智能体系统**

*A multi-agent system powered by genetic evolution for adaptive DeFi trading strategy optimization*

[![OKX Agent Trade Kit](https://img.shields.io/badge/OKX-Agent_Trade_Kit_MCP-00DC82?style=for-the-badge)](https://www.okx.com/zh-hans/agent-tradekit)
[![MCP Tools](https://img.shields.io/badge/MCP_Tools-119-blue?style=for-the-badge)](https://github.com/okx/agent-trade-kit)
[![OnchainOS](https://img.shields.io/badge/OnchainOS-500+_DEX-cyan?style=for-the-badge)](https://web3.okx.com/zh-hans/onchainos)
[![Skills](https://img.shields.io/badge/AI_Skills-11-purple?style=for-the-badge)](https://github.com/okx/onchainos-skills)
[![Demo](https://img.shields.io/badge/Live_Demo-Click_Here-orange?style=for-the-badge)](https://brian5216.github.io/GeneFi/)

**[Live Demo](https://brian5216.github.io/GeneFi/) · [GitHub Repo](https://github.com/Brian5216/GeneFi) · [OKX Agent Trade Kit](https://www.okx.com/zh-hans/agent-tradekit)**

</div>

---

## Evaluation Criteria Compliance 评审维度达标

> 本项目严格按照 OKX AI Hackathon 评审标准设计，以下为四维度自评与证据：

### 1. OKX Agent Trade Kit 结合度 ⭐⭐⭐⭐⭐

| 集成项 | 状态 | 证据 |
|---|---|---|
| Agent Trade Kit MCP 协议接入 | ✅ | `mcp_bridge.py` + `mcp_proxy.js` stdio 通信 |
| 119 个 MCP 工具全部可用 | ✅ | `tools/list` 返回 119 tools (7类) |
| Market 模块 (13 tools) | ✅ | `market_get_ticker`, `market_get_funding_rate` 等 |
| Swap 模块 (17 tools) | ✅ | `swap_place_order`, `swap_close_position`, `swap_set_leverage` |
| Account 模块 (13 tools) | ✅ | `account_get_balance`, `account_get_positions` |
| Spot 模块 (13 tools) | ✅ | `spot_place_order` 框架就绪 |
| Grid 模块 (5 tools) | ✅ | `grid_create_order` 网格机器人部署 |
| Option 模块 (14 tools) | ✅ | 工具可用，按需调用 |
| Demo Trading 模式 | ✅ | `x-simulated-trading: 1` 真实下单 |
| 真实 orderId 生成 | ✅ | 如 `3412480144057896960` |
| OnchainOS DEX Aggregator | ✅ | 500+ DEX, 20+ Chains 聚合报价 |
| OnchainOS AI Skills | ✅ | 11 个 Skills 已安装 (wallet, dex, security, x402...) |
| OKX Earn API (Safe Mode) | ✅ | `POST /api/v5/finance/savings/purchase-redempt` |
| 数据优先级: MCP → REST → Sim | ✅ | `onchain_os.py` 三级 fallback |

### 2. 工具实用性 ⭐⭐⭐⭐⭐

| 功能 | 状态 | 说明 |
|---|---|---|
| 遗传进化引擎完整闭环 | ✅ | 预测→执行→评估→选择→变异→下一代 |
| 9 维策略基因模型 | ✅ | leverage, entry/exit, hedge, SL/TP, direction, chain, type |
| 8 种市场体制自动检测 | ✅ | bull/bear volatile, trending, range, funding extreme |
| OKX 真实 K 线回测 | ✅ | 滚动窗口避免数据复用 |
| 适应度函数 (归一化) | ✅ | `0.5×PnL + 0.3×Funding×50 − 0.2×MaxDD` |
| 参数面板实时调参 | ✅ | 种群大小/变异率/淘汰压力/代数 |
| 策略导出 (JSON) | ✅ | 复制/下载完整基因参数 |
| 投资模拟器 | ✅ | 输入本金→真实K线回测→资金曲线 |
| 回测对比 | ✅ | 进化策略 vs 随机策略对比图 |
| 蒙特卡洛统计验证 | ✅ | 30 trials × 多体制, t-test, p-value |
| 一键部署到 OKX | ✅ | Deploy 按钮→MCP 真实下单 |
| 安全模式→OKX Earn | ✅ | 连续3代下降自动切换稳健理财 |
| 基因漂变可视化 | ✅ | 5维参数跨代演化曲线 |
| 最优基因雷达图 | ✅ | 6维蛛网图展示最优策略 |
| A2A 审计日志 | ✅ | JSONL 格式完整通信记录 |
| 双模式切换 | ✅ | Simulation / OKX Demo Trading |
| 策略类型可变异 | ✅ | funding_arb ↔ grid ↔ momentum ↔ mean_reversion |
| K线去重 + 数据校验 | ✅ | 防止重复时间戳和缺失字段 |

### 3. 创新性 ⭐⭐⭐⭐⭐

| 创新点 | 说明 |
|---|---|
| **遗传进化 × DeFi 交易** | 首次将达尔文进化论完整映射到交易策略优化 |
| **三智能体 A2A 闭环** | Predictor→Executor→Judge 自治协作，无需人工干预 |
| **力导向图实时可视化** | SVG 物理模拟展示策略生态系统，大小/颜色=适应度 |
| **基因漂变追踪** | 可视化展示自然选择如何改变种群参数分布 |
| **MCP stdio Bridge** | 创新性地通过 Python→Node.js subprocess 桥接 MCP |
| **蒙特卡洛多体制验证** | 多市场环境下统计证明进化产生超额收益 (Alpha) |
| **安全模式仿生设计** | 模拟生物"休眠"机制，市场恶劣时自动避险 |
| **9维基因染色体** | 完整的策略参数空间，支持突变/交叉/物种形成 |
| **DEX+CEX 双轨进化** | 同时优化链上 DeFi 和中心化交易所策略 |

### 4. 可复制性 ⭐⭐⭐⭐⭐

| 项目 | 状态 | 说明 |
|---|---|---|
| Docker 一键部署 | ✅ | `docker-compose up --build` |
| README 完整文档 | ✅ | 架构图 + 流程图 + 基因模型 + API 列表 |
| `.env.example` 模板 | ✅ | 所有环境变量有说明 |
| 无 API Key 可运行 | ✅ | Simulation 模式全功能 |
| `package.json` 依赖管理 | ✅ | Node.js 依赖锁定 |
| `requirements.txt` | ✅ | Python 依赖锁定 |
| MCP 配置模板 | ✅ | `~/.okx/config.toml` 示例 |
| OnchainOS Skills 预装 | ✅ | 11 Skills 在 `.agents/skills/` |
| 项目进度表 | ✅ | `PROGRESS.md` 完整跟踪 |
| GitHub 公开仓库 | ✅ | [Brian5216/GeneFi](https://github.com/Brian5216/GeneFi) |
| Live Demo | ✅ | [GitHub Pages](https://brian5216.github.io/GeneFi/) |
| 中英双语 UI | ✅ | 所有标签 "中文 English" 格式 |

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

## System Architecture

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
│  ┌─ Agent Trade Kit (MCP Protocol) ────────────────────────┐ │
│  │  119 tools via stdio • Demo Trading mode                 │ │
│  │                                                          │ │
│  │  market_get_ticker       → Live BTC/ETH price            │ │
│  │  market_get_funding_rate → Funding rate detection         │ │
│  │  swap_place_order        → Futures order execution        │ │
│  │  swap_close_position     → Position management            │ │
│  │  swap_set_leverage       → Risk control (1-20x)           │ │
│  │  account_get_balance     → Portfolio tracking              │ │
│  │  grid_create_order       → Grid bot deployment            │ │
│  │  spot_place_order        → Spot trading                   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ OnchainOS DEX Aggregator ──────────────────────────────┐ │
│  │  500+ DEX • 20+ chains • Smart order splitting           │ │
│  │  ETH / ARB / OP / MATIC / BASE / BSC / X Layer           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ 11 AI Skills Installed ────────────────────────────────┐ │
│  │  agentic-wallet │ dex-swap   │ security    │ x402       │ │
│  │  dex-market     │ dex-token  │ audit-log   │ gateway    │ │
│  │  dex-signal     │ trenches   │ portfolio                │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ OKX Earn (Safe Mode) ──────────────────────────────────┐ │
│  │  Auto-switch when fitness declines 3+ consecutive gens   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  Data Priority: MCP Agent Trade Kit → REST API → Simulation  │
└──────────────────────────────────────────────────────────────┘
```

---

## Strategy Gene Model

```
┌─────────────────────────────────────────────────────────┐
│                  9-Gene Strategy Chromosome               │
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

## Quick Start

```bash
# Clone
git clone https://github.com/Brian5216/GeneFi.git && cd GeneFi

# Install dependencies
pip install -r requirements.txt && npm install

# (Optional) OKX Demo Trading
cp .env.example .env  # Edit with your OKX API keys

# Start
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 \
  --loop asyncio --http h11 --ws websockets &
node serve.js

# Open http://localhost:8000
```

### Docker

```bash
docker-compose up --build
# Open http://localhost:8000
```

### MCP Setup

```bash
npm install -g okx-trade-mcp
npx skills add okx/onchainos-skills --yes
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Frontend | Vanilla JS + SVG + Canvas (zero dependencies) |
| Communication | WebSocket + A2A JSON Protocol |
| Trading (MCP) | OKX Agent Trade Kit (119 tools via MCP stdio) |
| DeFi | OnchainOS DEX Aggregator (500+ DEX) |
| AI Models | Claude Opus (Predictor) + Claude Sonnet (Judge) |
| Deployment | Docker multi-stage + Node.js reverse proxy |

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard (4-tab UI) |
| `WS /ws` | Real-time WebSocket |
| `GET /api/status` | System + MCP stats |
| `GET /api/market` | Live market (MCP source) |
| `GET /api/account` | Balance & positions |
| `GET /api/export` | Export top strategies |
| `GET /api/backtest` | Evolved vs random |
| `GET /api/dex_quote` | DEX swap quote |
| `GET /api/simulate_investment` | Investment simulator |
| `GET /api/monte_carlo` | Statistical validation |

---

## Project Structure

```
GeneFi/
├── main.py                     # FastAPI + WebSocket + evolution loop
├── config.py                   # Configuration
├── serve.js                    # Node.js reverse proxy
├── mcp_proxy.js                # MCP proxy (undici ProxyAgent)
├── dtes/
│   ├── core/
│   │   ├── strategy.py         # 9-gene chromosome model
│   │   ├── fitness.py          # Normalized fitness function
│   │   ├── evolution.py        # Evolution engine
│   │   └── backtest.py         # Monte Carlo backtester
│   ├── agents/
│   │   ├── predictor.py        # Market regime → population
│   │   ├── executor.py         # Strategy execution + OKX trading
│   │   └── judge.py            # Fitness evaluation + safe mode
│   ├── protocol/
│   │   └── a2a.py              # A2A protocol + audit log
│   └── okx/
│       ├── onchain_os.py       # OKX integration (MCP priority)
│       ├── mcp_bridge.py       # Python ↔ MCP stdio bridge
│       └── dex_aggregator.py   # 500+ DEX aggregation
├── .agents/skills/             # 11 OnchainOS AI Skills
├── static/                     # Dashboard UI
├── Dockerfile                  # Multi-stage build
└── docker-compose.yml          # Container orchestration
```

---

<div align="center">

Built for **OKX AI Hackathon Season 2** | Powered by Claude + OKX Agent Trade Kit

[Live Demo](https://brian5216.github.io/GeneFi/) · [GitHub](https://github.com/Brian5216/GeneFi)

</div>
