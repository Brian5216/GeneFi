# GeneFi — 当达尔文遇上 DeFi

搭载 @OKX Agent Trade Kit，我做了一个让交易策略自己"进化"的 AI Agent。

不是那种"帮你下单"的机器人。是一个会自己试错、自己淘汰、自己变强的系统。

---

## 从一个问题开始

我一直在想一个问题：为什么大多数交易策略用了一阵就不行了？

因为市场在变。牛市的参数到熊市就是送钱。趋势跟踪在震荡期会被反复打脸。资金费率套利在费率归零时毫无价值。

手动调参数？你调一次市场又变了。

所以我想：能不能让策略自己适应市场？

生物做了几十亿年的事就是适应环境。变异产生多样性，自然选择保留适者，交叉组合优秀基因。这就是达尔文进化论。

GeneFi 做的事情就是把这套逻辑搬到交易策略上。

---

## 它到底怎么运行的

### 策略 = 生物个体

GeneFi 里，一套交易策略就是一个"生物"。它的 DNA 由 9 个基因组成：

- **leverage**（1-20x）— 杠杆倍数
- **entry_threshold**（0.1-0.95）— 入场信号灵敏度
- **exit_threshold**（0.05-0.6）— 出场触发水平
- **hedge_ratio**（0-1.0）— 对冲比例
- **stop_loss_pct**（2-15%）— 止损
- **take_profit_pct**（5-30%）— 止盈
- **direction** — 做多 / 做空 / 中性
- **chain** — ETH / ARB / OP / MATIC / BASE / BSC
- **strategy_type** — 套利 / 网格 / 动量 / 均值回归

这 9 个参数定义了一个策略的全部行为。一个种群有 20 个这样的"个体"。

### 进化 = 一代代的生死

每一代，系统做五件事：

**第一步：检测市场体制**
从 OKX 拿到真实的 1H K 线，计算趋势和波动率，判断当前属于 8 种体制中的哪一种——牛市波动、熊市波动、趋势上行、趋势下行、高波动、资金费率极端（正/负）、震荡盘整。不同体制会影响后续策略生成的参数偏好。

**第二步：Predictor Agent 生成种群**
Claude Opus 根据市场体制，生成一批适合当前环境的策略。牛市时倾向于生成高杠杆做多策略，资金费率极端时倾向于生成套利策略。这不是随机生成——是有市场感知的智能孵化。

**第三步：Executor Agent 回测执行**
这是关键的一步。每个策略在真实 OKX K 线数据上跑一遍回测。不是用同一段数据反复跑——每一代用不同的 K 线窗口（滑动窗口），避免过拟合。

回测过程中会计算：PnL（盈亏）、资金费率收益（对套利策略）、最大回撤、胜率、夏普比率。

在 Demo Trading 模式下，精英策略还会通过 Agent Trade Kit MCP 发一笔真实的 OKX 订单——拿到真实的 orderId，然后立刻平仓。这不是为了赚钱，是为了证明整个执行链路是通的。

**第四步：Judge Agent 评分排名**
Claude Sonnet 对每个策略打分。适应度函数：

```
Score = 0.5 × PnL + 0.3 × FundingYield × 50 − 0.2 × MaxDrawdown
```

为什么 FundingYield 要乘 50？因为原始资金费率数值太小（通常是 0.0001 量级），不归一化的话这个维度在适应度函数里几乎没有存在感，套利策略永远得不到公平评价。这个系数是调试了很多轮之后定的。

排完名：前 20% 是精英（保留），中间 50% 存活，后 30% 淘汰。

**第五步：变异 + 交叉 → 下一代**
精英之间交叉产生后代（60% 概率），其余位置由存活个体变异填充。变异不只改数值参数——策略类型本身也可以变。一个套利策略可能在几代后突变成动量策略，如果后者更适应当前市场。

然后回到第一步，下一代开始。

每一代大约 1.5 秒。跑 15 代，你能看到种群从随机噪声中"长出"结构来。适应度曲线先下降（淘汰弱者），然后逐步收敛上升。

---

## Agent Trade Kit 到底集成了什么

这是整个项目最核心的部分。GeneFi 不是在自己的沙盒里跑模拟——它通过 MCP stdio 协议直接调用 OKX Agent Trade Kit 的 119 个工具。

技术实现是这样的：

```
GeneFi Agent (Python) → mcp_bridge.py → mcp_proxy.js → okx-trade-mcp (Node.js) → OKX API
```

为什么中间有个 `mcp_proxy.js`？因为 okx-trade-mcp 内部用了 Node.js 的 undici fetch，在有 HTTP 代理的网络环境下不会自动走代理。我写了一个 wrapper，在加载 MCP server 之前用 `undici.ProxyAgent` + `setGlobalDispatcher` 注入代理。这个解决方案花了不少时间调试，但最终让 MCP 在任何网络环境下都能工作。

实际调用的 MCP 工具：

**Market 模块（13 tools）**
- `market_get_ticker` — 获取 BTC-USDT 实时价格（$68,730.8，每次都是真实数据）
- `market_get_funding_rate` — 获取 BTC-USDT-SWAP 资金费率（如 -0.0000785）
- `market_get_candles` — 获取 1H K 线用于趋势计算和策略回测
- `market_get_orderbook` — 获取深度数据计算价差

**Swap 模块（17 tools）**
- `swap_place_order` — 下合约市价单。真实的。orderId: `3412480144057896960`
- `swap_close_position` — 平仓。net_mode 下 posSide 传 "net"
- `swap_set_leverage` — 设置杠杆。每个策略根据基因参数动态调整

**Account 模块（13 tools）**
- `account_get_balance` — 查 Demo Trading 余额（$82,755.19）
- `account_get_positions` — 查活跃仓位

**Grid 模块（5 tools）**
- `grid_create_order` — 部署网格交易机器人

还有 Spot（13 tools）和 Option（14 tools）模块，框架已就绪，按需调用。

整个数据流有三级优先级：MCP Agent Trade Kit（优先）→ REST API（回退）→ 本地模拟（兜底）。代码里可以清楚看到这个 fallback 链——`onchain_os.py` 的每个方法都先尝试 MCP，失败了才走 REST，再失败才用模拟数据。

---

## OnchainOS 生态

CEX 交易之外，GeneFi 还接入了 OKX 的链上生态：

**DEX Aggregator（500+ DEX，20+ 链）**
进化引擎需要帮策略选择最优交易链。比如同一笔 ETH 交易，在 Arbitrum 上 gas 可能只要 $0.2，在 Ethereum 主网要 $15。DEX Aggregator 的 `find_best_chain` 方法会并行查询所有支持的链，比较 net_amount（扣除 gas 后的实际到账量），返回最优链。

**11 个 AI Skills 已安装**
通过 `npx skills add okx/onchainos-skills --yes` 安装了完整的 OnchainOS Skills 套件：
agentic-wallet / dex-swap / dex-market / dex-signal / dex-token / dex-trenches / onchain-gateway / security / wallet-portfolio / x402-payment / audit-log

这些 Skills 安装在 `.agents/skills/` 目录下，可以被任何兼容的 AI Agent 调用。

**OKX Earn 安全模式**
这是一个仿生设计。当种群适应度连续 3 代下降时，Judge Agent 会判定"环境恶劣"，触发安全模式——自动调用 OKX Earn API（`POST /api/v5/finance/savings/purchase-redempt`）把资产转入稳健理财。等市场恢复后再赎回继续交易。

这就像生物在极端环境下进入休眠状态。不是逃跑，是等待更好的进化时机。

---

## 它真的有用吗

这是最诚实的部分。

GeneFi 内置了蒙特卡洛统计验证。不是跑一次说"看，赚了"，而是：
- 30 次独立试验
- 每次在不同的市场体制下运行
- 计算 Sharpe Ratio、最大回撤、年化 Alpha
- 用 Welch's t-test 检验进化策略是否显著优于随机策略
- p-value < 0.05 才算统计显著

投资模拟器让用户输入一笔本金（比如 $10,000），在真实 OKX K 线上跑一遍回测，看到完整的资金曲线、最高点、最低点、最大回撤，以及和随机策略的 Alpha 对比。

说实话，不是每一次跑都能赚钱。市场下行的时候，进化出来的策略也会亏——但它会比随机策略亏得少。而且安全模式会在连续亏损时自动介入。

这不是一个"保证赚钱"的系统。它是一个"让策略自动适应、自动风控、有统计基础"的系统。

---

## 可以直接跑

```bash
git clone https://github.com/Brian5216/GeneFi.git
cd GeneFi
pip install -r requirements.txt && npm install
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --loop asyncio --http h11 --ws websockets &
node serve.js
```

打开 `http://localhost:8000`，点「启动 Start」就开始进化。

或者一行 Docker：
```bash
docker-compose up --build
```

**不需要 OKX API Key 也能跑。** Simulation 模式下所有功能完整可用——进化引擎、可视化、投资模拟器、策略导出，全都能用。想连真实的 OKX Demo Trading？在 `.env` 里填上 API Key，在设置面板切换到 "OKX Demo Trading" 模式就行。

前端有 4 个 Tab：
- **智能体 Agents** — 三个 Agent 的实时状态
- **OKX 生态** — MCP 调用次数、工具使用数、DEX 最优链、实时行情
- **关于 About** — 6 大核心优势、5 步进化流程图、技术栈
- **设置 Config** — 种群大小、变异率、淘汰压力、执行模式、投资模拟器

力导向图可视化会实时展示每个策略个体——大小代表适应度，颜色从红（弱）到绿（强），字母标识策略类型（F=套利、G=网格、M=动量、R=回归）。看着弱者消失、强者繁殖，基因漂变图上参数曲线逐渐收敛——这就是自然选择在你眼前发生。

---

## 技术细节

- **后端**：Python 3.11 + FastAPI + Uvicorn
- **前端**：Vanilla JS + SVG 物理模拟 + Canvas 图表（零框架依赖）
- **通信**：WebSocket 实时推送 + A2A JSON Protocol
- **MCP 集成**：mcp_bridge.py（Python→MCP stdio）+ mcp_proxy.js（undici 代理注入）
- **链上**：OKX Agent Trade Kit 119 tools + OnchainOS DEX 500+ + 11 Skills
- **部署**：Docker 多阶段构建 + Node.js 反向代理

全部代码开源：https://github.com/Brian5216/GeneFi
展示页面：https://brian5216.github.io/GeneFi/

---

这不是一个周末的 demo。这是一个从达尔文到 DeFi 的完整技术验证——有真实的 OKX API 调用，有统计学的严谨验证，有可以直接克隆运行的完整代码。

如果你也觉得"让策略自己进化"是一个值得探索的方向，欢迎 clone 下来跑一跑。

#OKXAI松 #OKXAgentTradeKit #DeFi #AIAgent #GeneticAlgorithm #OnchainOS @OKX @OKXCNWeb3
