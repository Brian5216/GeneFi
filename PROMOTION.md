# GeneFi - 参赛宣传文稿

---

## Twitter/X 发布版（中英双语）

---

### 主推文 Main Tweet

GeneFi | 基因金融 — 让交易策略像生物一样进化

把每一套交易策略当作一个"生物个体"，用遗传变异 + 自然选择，让策略种群在真实市场中自动进化、适者生存。

核心架构：
Predictor (Claude Opus) 检测市场体制，孵化策略种群
Executor (OKX Agent Trade Kit) 在 OKX 模拟盘真实下单验证
Judge (Claude Sonnet) 评分淘汰，驱动下一轮进化

不是回测拟合，是真正的自适应进化。

GeneFi | Gene + DeFi — Trading strategies that evolve like living organisms.

Each strategy is a "biological individual" with DNA (leverage, direction, hedge ratio...). Through mutation, crossover, and natural selection, the population self-adapts to survive real market conditions.

Architecture:
Predictor (Claude Opus): Detects market regime, breeds strategy population
Executor (OKX Agent Trade Kit): Executes on OKX Demo Trading with real orders
Judge (Claude Sonnet): Fitness scoring, elimination, drives next evolution cycle

Not curve-fitting. Real adaptive evolution.

@okxchinese @GeminiApp

---

### 技术亮点推文 Thread (1/5)

[1/5] GeneFi 技术深度解析

策略基因模型 Strategy Gene DNA：
- 9个可变异参数：杠杆、入场阈值、出场阈值、对冲比、止损、止盈、方向、链、策略类型
- 4种策略物种：资金费率套利 / 网格交易 / 动量追踪 / 均值回归
- 每个参数都会在进化中被自然选择筛选

---

[2/5] OKX Agent Trade Kit 深度集成

真实 API 调用，不是模拟：
- Market Ticker API — 实时行情驱动进化
- Funding Rate API — 资金费率套利策略依据
- Candles API — 1H K线回测，每代用不同时间窗口
- Trade Order API — 模拟盘真实下单（orderId 可查）
- Grid Bot API — 网格机器人部署
- Earn API — 安全模式自动切换理财
- Set Leverage API — 动态调整杠杆
- Position API — 持仓追踪

8个 OKX API 端点，完整覆盖交易全链路。

---

[3/5] 进化引擎核心逻辑

适应度函数：
Score = 0.5 x PnL% + 0.3 x FundingYield - 0.2 x MaxDrawdown

种群选择：
Top 20% = 精英（保留 + 繁殖）
Middle 50% = 存活（保留）
Bottom 30% = 淘汰（被后代替换）

蒙特卡洛验证：30轮随机模拟 + Welch's t-test 统计显著性检验
证明进化策略显著优于随机策略（p < 0.05）

---

[4/5] 安全模式 — 生物学的"休眠"

当种群适应度连续3代下降：
1. Judge Agent 触发安全模式
2. 自动调用 OKX Earn API 将资产存入稳健理财
3. 降低变异率，保护优质基因
4. 市场恢复后自动赎回，重启进化

这不是简单的止损。是让策略像冬眠动物一样，在恶劣环境中保存实力。

---

[5/5] 一键体验 GeneFi

Docker 一键部署：
docker-compose up --build
打开 http://localhost:8000

无需 API Key 也能跑 Simulation 模式
配置 OKX Demo Trading Key 即可真实下单

开源地址：[GitHub链接]

技术栈：Python FastAPI + Node.js Proxy + SVG Force-Directed Graph + WebSocket Real-time

---

## OKX 星球发布版（纯中文，更详细）

---

### 标题
GeneFi 基因金融 — 用遗传进化驱动 DeFi 交易策略自适应优化

### 正文

你有没有想过，交易策略也可以像生物一样进化？

GeneFi 是一个基于遗传进化算法的多智能体自适应交易系统。它把每套交易策略视为一个"生物个体"，通过变异、交叉和自然选择，让策略种群在真实市场数据中自动进化。

#### 为什么叫 GeneFi？

Gene（基因）+ DeFi（去中心化金融）= GeneFi

每个策略都有自己的"DNA"——9个可变异的基因参数。优秀的策略会繁殖后代，糟糕的策略会被自然淘汰。经过多代进化，种群会自动收敛到当前市场最优解。

#### 三大智能体协作

| 智能体 | 角色 | 使用模型 |
|---|---|---|
| Predictor 预测者 | 检测市场体制（牛市/熊市/震荡等8种），生成市场自适应策略种群 | Claude Opus |
| Executor 执行者 | 在 OKX 模拟盘真实下单，收集 PnL、回撤、胜率等数据 | OKX Agent Trade Kit |
| Judge 裁判者 | 适应度评分，排名淘汰，触发安全模式 | Claude Sonnet |

三个智能体通过 A2A 协议通信，形成"预测→执行→评估→进化"的闭环。

#### OKX Agent Trade Kit 深度集成

GeneFi 不是简单调用一两个 API。我们覆盖了 OKX 交易工具链的 8 个核心端点：

1. **实时行情** — 真实 BTC/ETH 价格驱动进化决策
2. **资金费率** — 捕捉资金费率套利机会
3. **K线数据** — 1小时K线用于策略回测，每代用不同时间窗口避免过拟合
4. **合约下单** — 模拟盘真实下单，返回真实 orderId
5. **网格机器人** — 自动部署网格交易策略
6. **OKX Earn** — 安全模式自动存入稳健理财
7. **杠杆设置** — 根据策略基因动态调整
8. **持仓管理** — 实时追踪仓位和盈亏

所有交易都在 OKX Demo Trading 模式下执行（x-simulated-trading: 1），安全可靠。

#### 数学验证：进化真的有效吗？

我们用蒙特卡洛方法验证：

- 30轮随机策略模拟作为基线
- 进化策略 vs 随机策略的适应度对比
- Welch's t-test 统计显著性检验
- 结果：进化策略显著优于随机策略（p < 0.05）

这不是"看起来有效"，而是统计学意义上的"确实有效"。

#### 安全模式 — 策略的"冬眠"

当市场环境恶化，连续3代适应度下降时：
- Judge Agent 自动触发安全模式
- 调用 OKX Earn API 将资产转入稳健理财
- 降低变异率，保护优质基因不被破坏
- 市场恢复后自动赎回，重启进化

这是从生物学中借鉴的"休眠"策略——在恶劣环境中保存实力，等待时机。

#### 可视化进化过程

GeneFi 提供力导向图可视化：
- 每个节点 = 一个策略个体
- 节点大小 = 适应度高低
- 节点颜色 = 绿色(盈利) → 红色(亏损)
- 节点标签 = 策略类型（F=套利, G=网格, M=动量, R=回归）
- 实时动画展示"出生"和"死亡"

加上适应度时间线、基因漂变图、策略排行榜，完整展示进化过程。

#### 用户可以做什么？

1. **启动进化** — 一键开始，看策略种群自动进化
2. **调参** — 实时调整种群大小、变异率、淘汰压力
3. **导出策略** — 进化出的最优策略可导出为 JSON
4. **一键部署** — 最优策略直接部署到 OKX 模拟盘
5. **投资模拟** — 输入本金，看进化策略的历史收益曲线
6. **回测对比** — 进化策略 vs 随机策略的对比图

#### 一键体验

```bash
# Docker 部署
docker-compose up --build
# 打开 http://localhost:8000

# 或本地运行
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001
node serve.js
```

无需 API Key 也能体验 Simulation 模式。
配置 OKX Demo Trading API Key 后可真实下单。

---

## 配图建议 Visual Assets

1. **架构图** — 三智能体 A2A 闭环图（Predictor → Executor → Judge → Evolution）
2. **进化截图** — 力导向图 + 适应度曲线 + 基因漂变图
3. **OKX 集成截图** — 展示真实 orderId、账户余额、API 调用日志
4. **回测对比图** — 进化 vs 随机的适应度对比
5. **蒙特卡洛结果** — p-value 和统计显著性
6. **安全模式截图** — 触发 Earn 的界面

建议用 GIF 录屏展示一轮完整进化过程（约 30 秒）。

---

## 提交 Checklist

- [ ] Twitter 发布主推文 + 技术 Thread
- [ ] @okxchinese @GeminiApp
- [ ] 三连官方置顶推文
- [ ] OKX 星球发布详细版
- [ ] 填写 Google Form 报名
- [ ] 准备 30 秒演示 GIF
- [ ] 确认 GitHub 仓库公开
