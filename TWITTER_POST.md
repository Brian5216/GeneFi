# GeneFi — 当达尔文遇上 DeFi

搭载 @OKX Agent Trade Kit，我设计了一个让交易策略自己"进化"的 AI Agent。

## 它能做什么？

GeneFi 把每套交易策略当成一个生物个体。给它一个种群，它会自己变异、交叉、淘汰，经过一代代自然选择，进化出适应当前市场的最优策略。

不需要你手动调参数。不需要你盯盘。它自己来。

## 怎么做到的？

三个 AI Agent 组成一个闭环：

- **Predictor**（Claude Opus）：分析市场，检测当前属于 8 种体制中的哪一种（牛市波动、趋势下行、资金费率极端……），然后生成适合当前环境的策略种群
- **Executor**（OKX OnchainOS）：通过 Agent Trade Kit MCP 协议执行每个策略——真的下单、真的平仓、真的查余额。不是模拟，是 Demo Trading 模式下的真实 API 调用
- **Judge**（Claude Sonnet）：给每个策略打分，精英保留、弱者淘汰、新个体通过变异和交叉诞生

每一代大约 1.5 秒。跑 15 代，你就能看到策略种群从随机噪声中"长出"一套赚钱的参数组合。

## Agent Trade Kit 集成了什么？

这是让我最兴奋的部分——GeneFi 通过 MCP stdio 协议直接调用 Agent Trade Kit 的 119 个工具：

**Market 模块**：market_get_ticker 拿实时 BTC 价格、market_get_funding_rate 检测资金费率、market_get_candles 获取 K 线做回测

**Swap 模块**：swap_place_order 下合约单、swap_close_position 平仓、swap_set_leverage 控制杠杆

**Account 模块**：account_get_balance 查余额、account_get_positions 看持仓

**Grid 模块**：grid_create_order 一键部署网格机器人

整个数据流是：MCP Agent Trade Kit（优先）→ REST API（回退）→ 本地模拟（兜底）。评审可以在代码里清楚看到这个三级优先级。

实际调用产生了真实的 orderId（如 3412480144057896960），这不是模拟数据。

## OnchainOS 生态集成

除了 CEX 交易，GeneFi 还接入了 OnchainOS：

- **DEX Aggregator**：500+ DEX、20+ 链的聚合报价，用来帮进化引擎选择最优交易链
- **11 个 AI Skills 已安装**：agentic-wallet、dex-swap、dex-market、dex-signal、dex-token、dex-trenches、onchain-gateway、security、wallet-portfolio、x402-payment、audit-log
- **OKX Earn**：当种群适应度连续 3 代下降时，自动把资产切换到 Earn 稳健理财——这是模拟生物"休眠"的设计

## 策略基因长什么样？

每个策略有 9 个基因：

```
leverage (1-20x) | entry_threshold | exit_threshold
hedge_ratio (0-1) | stop_loss (2-15%) | take_profit (5-30%)
direction (Long/Short/Neutral) | chain (ETH/ARB/OP/BASE...)
strategy_type (Arb/Grid/Momentum/MeanReversion)
```

这 9 个参数会在进化过程中被突变和交叉。策略类型也可以变——一个套利策略可能在几代后变异成动量策略，如果市场环境更适合后者。

适应度函数：`Score = 0.5 × PnL + 0.3 × FundingYield × 50 − 0.2 × MaxDrawdown`

## 它真的能赚钱吗？

GeneFi 内置了蒙特卡洛统计验证：30 次独立试验 × 多市场体制，用 t 检验判断进化策略是否显著优于随机策略。

投资模拟器可以让你输入一笔本金，在真实 OKX K 线上回测，看到完整的资金曲线和 Alpha 超额收益。

当然，过去表现不代表未来——但至少这是一个有统计基础的系统，而不是拍脑袋的参数。

## 可复制性

```bash
git clone https://github.com/Brian5216/GeneFi.git
cd GeneFi
pip install -r requirements.txt && npm install
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 &
node serve.js
# 打开 http://localhost:8000
```

或者一行 Docker：`docker-compose up --build`

不需要 OKX API Key 也能跑——Simulation 模式下所有功能完整可用。想连 Demo Trading？填上 Key 就能切换。

- GitHub: https://github.com/Brian5216/GeneFi
- Live Demo: https://brian5216.github.io/GeneFi/
- 技术栈：Python FastAPI + Vanilla JS + SVG + WebSocket + OKX MCP + Docker

---

#OKXAI松 #OKXAgentTradeKit #DeFi #AIAgent #GeneticAlgorithm #OnchainOS @OKX @OKXCNWeb3
