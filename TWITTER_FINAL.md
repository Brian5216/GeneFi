# GeneFi — 当达尔文遇上 DeFi

搭载 @OKX Agent Trade Kit，我做了一个让交易策略自己"进化"的 AI Agent。

不是那种"帮你下单"的机器人。是一个会自己试错、自己淘汰、自己变强的系统。

—————

从一个问题开始

为什么大多数交易策略用了一阵就不行了？因为市场在变。牛市的参数到熊市就是送钱。趋势跟踪在震荡期会被反复打脸。资金费率套利在费率归零时毫无价值。

手动调参数？你调一次市场又变了。

所以我想：能不能让策略自己适应市场？生物做了几十亿年的事就是适应环境——变异产生多样性，自然选择保留适者，交叉组合优秀基因。GeneFi 把这套逻辑搬到交易策略上。

—————

策略就是生物个体

GeneFi 里每套交易策略就是一个"生物"，它的 DNA 由 9 个基因组成：

leverage（1-20x 杠杆）、entry_threshold（入场灵敏度）、exit_threshold（出场水平）、hedge_ratio（对冲比例）、stop_loss（2-15% 止损）、take_profit（5-30% 止盈）、direction（做多/做空/中性）、chain（ETH/ARB/OP/MATIC/BASE/BSC）、strategy_type（套利/网格/动量/均值回归）

这 9 个参数定义了策略的全部行为。一个种群有 20 个这样的"个体"。

—————

进化怎么运行：5 步闭环

每一代系统做五件事：

第一步：检测市场体制。从 OKX 拿到真实的 1H K 线，计算趋势和波动率，自动判断 8 种体制——牛市波动、熊市波动、趋势上行、趋势下行、高波动、资金费率极端（正/负）、震荡盘整。

第二步：Predictor Agent（Claude Opus）生成种群。根据体制生成适合当前环境的策略。牛市时倾向高杠杆做多，资金费率极端时倾向套利。不是随机生成——是有市场感知的智能孵化。

第三步：Executor Agent 回测执行。每个策略在真实 OKX K 线上跑回测。每一代用不同的 K 线窗口（滑动窗口），避免过拟合。回测计算 PnL、资金费率收益、最大回撤、胜率、夏普比率。在 Demo Trading 模式下，精英策略还会通过 MCP 发一笔真实 OKX 订单——orderId: 3412480144057896960，然后立刻平仓。

第四步：Judge Agent（Claude Sonnet）评分排名。适应度函数：Score = 0.5 × PnL + 0.3 × FundingYield × 50 − 0.2 × MaxDrawdown。为什么 FundingYield 要乘 50？因为原始资金费率数值太小（0.0001 量级），不归一化的话套利策略永远得不到公平评价。排完名：前 20% 精英保留，中间 50% 存活，后 30% 淘汰。

第五步：变异 + 交叉产生下一代。精英交叉产生后代（60% 概率），其余由存活个体变异填充。策略类型本身也可以变——套利可能几代后变成动量策略。

每一代约 1.5 秒。跑 15 代，策略种群从随机噪声中"长出"结构。

—————

Agent Trade Kit 集成了什么

这是最核心的部分。GeneFi 通过 MCP stdio 协议直接调用 Agent Trade Kit 的 119 个工具。

数据流：GeneFi Agent (Python) → mcp_bridge.py → mcp_proxy.js → okx-trade-mcp (Node.js) → OKX API

为什么有个 mcp_proxy.js？因为 okx-trade-mcp 内部用了 undici fetch，在有 HTTP 代理的网络环境下不走代理。我写了一个 wrapper 用 undici.ProxyAgent + setGlobalDispatcher 注入代理，让 MCP 在任何环境下都能工作。

实际调用的工具：

Market 模块（13 tools）：market_get_ticker 获取实时 BTC 价格 $68,730.8；market_get_funding_rate 获取资金费率如 -0.0000785；market_get_candles 获取 K 线做回测；market_get_orderbook 获取深度。

Swap 模块（17 tools）：swap_place_order 下合约市价单，真实 orderId 3412480144057896960；swap_close_position 平仓，net_mode 下 posSide 传 net；swap_set_leverage 每个策略根据基因参数动态调整杠杆。

Account 模块（13 tools）：account_get_balance 查 Demo Trading 余额 $82,755.19；account_get_positions 查活跃仓位。

Grid 模块（5 tools）：grid_create_order 部署网格机器人。

还有 Spot（13 tools）和 Option（14 tools）模块框架就绪。

整个数据流三级优先级：MCP Agent Trade Kit 优先 → REST API 回退 → 本地模拟兜底。代码里每个方法都先尝试 MCP，失败走 REST，再失败才用模拟。

—————

OnchainOS 生态

CEX 之外，GeneFi 还接入了 OnchainOS：

DEX Aggregator：500+ DEX、20+ 链聚合报价。find_best_chain 方法并行查询所有链，比较扣除 gas 后的 net_amount，返回最优链。同一笔 ETH 交易，Arbitrum gas $0.2，Ethereum 主网 $15。

11 个 AI Skills 已安装：通过 npx skills add okx/onchainos-skills 安装了 agentic-wallet、dex-swap、dex-market、dex-signal、dex-token、dex-trenches、onchain-gateway、security、wallet-portfolio、x402-payment、audit-log。

OKX Earn 安全模式：种群适应度连续 3 代下降时，Judge Agent 判定"环境恶劣"，自动调用 Earn API（POST /api/v5/finance/savings/purchase-redempt）把资产转入稳健理财。等市场恢复后赎回。这是模拟生物休眠——不是逃跑，是等待更好的进化时机。

—————

它真的有用吗

GeneFi 内置蒙特卡洛统计验证：30 次独立试验 × 多市场体制，计算 Sharpe Ratio、最大回撤、年化 Alpha，用 Welch's t-test 检验进化是否显著优于随机。p-value < 0.05 才算显著。

投资模拟器让你输入本金（比如 $10,000），在真实 OKX K 线上回测，看到资金曲线和 Alpha 对比。

说实话，不是每次都赚钱。市场下行时进化策略也会亏——但比随机策略亏得少。安全模式会在连续亏损时自动介入。

这不是"保证赚钱"的系统。是让策略自动适应、自动风控、有统计基础的系统。

—————

可以直接跑

git clone https://github.com/Brian5216/GeneFi.git
cd GeneFi
pip install -r requirements.txt && npm install
然后启动后端和前端，打开 localhost:8000

或者 Docker 一行：docker-compose up --build

不需要 OKX API Key 也能跑——Simulation 模式下所有功能完整可用。想连 Demo Trading？填上 Key 切换模式就行。

前端 4 个 Tab：智能体 Agents（三个 Agent 实时状态）、OKX 生态（MCP 调用数、DEX 最优链、行情）、关于 About（6 大优势、进化流程图）、设置 Config（调参+投资模拟器）。

力导向图可视化实时展示每个策略——大小代表适应度，颜色从红到绿，字母标识类型（F=套利、G=网格、M=动量、R=回归）。看着弱者消失、强者繁殖，基因漂变图上参数曲线逐渐收敛——自然选择在你眼前发生。

—————

技术栈

后端 Python 3.11 + FastAPI + Uvicorn，前端 Vanilla JS + SVG 物理模拟 + Canvas（零框架依赖），通信 WebSocket + A2A JSON Protocol，MCP 集成 mcp_bridge.py + mcp_proxy.js，链上 OKX Agent Trade Kit 119 tools + OnchainOS DEX 500+ + 11 Skills，部署 Docker 多阶段构建 + Node.js 反向代理。

代码开源：https://github.com/Brian5216/GeneFi
展示页面：https://brian5216.github.io/GeneFi/

—————

这不是一个周末的 demo。这是一个从达尔文到 DeFi 的完整技术验证——有真实的 OKX API 调用，有统计学的严谨验证，有可以直接克隆运行的完整代码。

如果你也觉得"让策略自己进化"是一个值得探索的方向，欢迎 clone 下来跑一跑。

#OKXAI松 #OKXAgentTradeKit #DeFi #AIAgent #GeneticAlgorithm #OnchainOS @OKX @OKXCNWeb3
