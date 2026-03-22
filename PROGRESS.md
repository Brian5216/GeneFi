# GeneFi 项目进度表 | Project Progress Tracker

> 最后更新: 2026-03-23 22:30

## 评审维度目标 Scoring Targets

| 维度 | 当前 | 目标 | 差距 |
|---|---|---|---|
| OKX Agent Trade Kit 结合度 | 6.5→**9.5** | 9+ | ✅ MCP 119 tools + Demo Trading |
| 工具实用性 | 7.0→**9.0** | 9+ | ✅ P0 bug 全修 + 真实下单 |
| 创新性 | 8.5→**8.5** | 9+ | 需先发推特 |
| 可复制性 | 7.5→**8.5** | 9+ | 需在线 Demo + 演示视频 |

---

## P0 - 核心 Bug 修复（必须完成，影响评审判分）

| # | Bug | 文件 | 严重度 | 状态 |
|---|---|---|---|---|
| 1 | direction 覆盖 strategy_type 逻辑 | backtest.py:177 | CRITICAL | [x] 改为 filter 模式 |
| 2 | Live PnL 膨胀 100x（*100 多余） | executor.py:393 | CRITICAL | [x] 去掉 *100 |
| 3 | fitness 适应度函数 funding 分量太小 | fitness.py:29 | MEDIUM | [x] funding_yield *50 归一化 |
| 4 | 快照包含未评分新生儿（fitness=0） | evolution.py:177 | MEDIUM | [x] 用 scored_pop |
| 5 | K线去重 + candle 数据验证 | executor.py:181 | MEDIUM | [x] 去重 + key 检查 |
| 6 | backtest.py funding 被 *0.1 压缩 | backtest.py:206 | LOW | [x] 改为 /8 |
| 7 | strategy_type 永远不会被变异 | strategy.py mutate() | LOW | [x] 加 20% 概率变异 |
| 8 | 缺少 candle 数据验证 | executor.py:181 | LOW | [x] 合并到 #5 |

## P1 - Agent Trade Kit MCP 集成（评审最大差距）

| # | 任务 | 状态 |
|---|---|---|
| 1 | 安装 okx-trade-mcp + 配置 config.toml | [x] 119 tools, Demo mode |
| 2 | 创建 MCP Bridge (mcp_bridge.py + mcp_proxy.js) | [x] undici proxy 解决网络问题 |
| 3 | OnchainOS 优先走 MCP (行情+下单+平仓+余额) | [x] source=mcp_agent_trade_kit |
| 4 | 市场数据显示 MCP 来源 | [x] 前端可见 MCP 标识 |
| 5 | README 展示 MCP 集成证据 | [x] 工具列表+架构图 |

## P2 - OnchainOS 生态集成（加分项）

| # | 任务 | 涉及工具 | 状态 |
|---|---|---|---|
| 1 | 接入 OnchainOS Skills (11 Skills) | AI Skills | [x] npx skills add 安装完成 |
| 2 | DEX 聚合 API (500+ DEX) | DEX API | [x] dex_aggregator.py + find_best_chain |
| 3 | 前端展示 MCP + DEX 集成状态 | UI | [x] 双卡片展示 |
| 4 | API 端点 /api/dex_quote | REST | [x] 跨链最优链查询 |

## P3 - 产品完善

| # | 任务 | 状态 |
|---|---|---|
| 1 | Tab 分模块重构 (Agents/OKX/About/Config) | [x] 4个Tab |
| 2 | About 系统介绍 (6优势+流程图+技术栈) | [x] 完整展示 |
| 3 | 空状态处理 + 控制台零错误 | [x] canvas-empty + leaderboard hint |
| 4 | 双语统一 + CSS 规范化 | [x] cfg-select/cfg-input 类名 |

## P4 - 发布准备

| # | 任务 | 状态 |
|---|---|---|
| 1 | 在线 Demo 部署（Railway/Render） | [ ] |
| 2 | 推特发布素材（GIF/截图） | [ ] |
| 3 | 录制 2 分钟演示视频 | [ ] |
| 4 | 提交作品 | [ ] |

---

## 未解决问题 Open Issues

| # | 问题 | 优先级 | 备注 |
|---|---|---|---|
| 1 | 跨链路由无真实 API 可调用 | LOW | OnchainOS DEX API 可能解决 |
| 2 | 进化算法无数学收敛性证明 | MEDIUM | 蒙特卡洛已部分解决 |
| 3 | Node 代理频繁崩溃 | HIGH | 需要 process manager |
| 4 | Grid Bot API 在 Demo Trading 返回 404 | MEDIUM | 可能需要不同的端点 |
