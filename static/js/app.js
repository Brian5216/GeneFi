/**
 * GeneFi Main Application
 * GeneFi 主应用 - WebSocket 客户端 + UI 状态管理
 * WebSocket client + UI state management
 */

let ws = null;
let viz = null;
let isEvolving = false;
let fitnessHistory = [];
let totalEliminated = 0;
let totalTrades = 0;
let balanceHistory = [];

// ─── Initialize 初始化 ───────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    viz = new EvolutionViz('evolution-canvas');
    connectWebSocket();
    initFitnessChart();
});

// ─── WebSocket 连接 ──────────────────────────────

function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws`;
    console.log('[GeneFi] Connecting WS to:', wsUrl);
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        document.getElementById('conn-dot').className = 'connection-dot connected';
        addLog('system', '已连接到 GeneFi 服务器 Connected to GeneFi server');
        fetchAccountInfo();
    };

    ws.onclose = () => {
        document.getElementById('conn-dot').className = 'connection-dot disconnected';
        addLog('system', '连接断开，正在重连… Disconnected. Reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
        document.getElementById('conn-dot').className = 'connection-dot disconnected';
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleEvent(msg.event, msg.data);
    };
}

function sendCommand(command, params = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ command, ...params }));
    }
}

// ─── Event Handlers 事件处理 ─────────────────────

function handleEvent(event, data) {
    switch (event) {
        case 'init':
            handleInit(data);
            break;
        case 'population_initialized':
            handlePopulationInit(data);
            break;
        case 'generation_result':
            handleGenerationResult(data);
            break;
        case 'generation_start':
            addLog('system', `第 ${data.generation} 代进化启动… Generation ${data.generation} starting...`);
            break;
        case 'selection_complete':
            handleSelection(data);
            break;
        case 'generation_complete':
            break;
        case 'market_data':
            updateMarketDisplay(data);
            break;
        case 'a2a_message':
            handleA2AMessage(data);
            break;
        case 'evolution_complete':
            handleEvolutionComplete(data);
            break;
        case 'evolution_stopped':
            setEvolvingState(false);
            addLog('system', '进化已停止 Evolution stopped');
            break;
        case 'reset':
            handleReset();
            break;
        case 'stats':
            updateStats(data);
            break;
    }
}

function handleInit(data) {
    if (data.population && data.population.length > 0) {
        viz.updatePopulation(data.population);
    }
    if (data.stats) updateStats(data.stats);
    if (data.history) {
        fitnessHistory = data.history.map(h => ({
            gen: h.generation,
            avg: h.avg_fitness,
            best: h.best_fitness,
            worst: h.worst_fitness,
        }));
        drawFitnessChart();
    }
    addLog('system', 'GeneFi 初始化完成，准备就绪 GeneFi initialized. Ready for evolution.');
}

function handlePopulationInit(data) {
    // Hide empty state
    const emptyEl = document.getElementById('canvas-empty');
    if (emptyEl) emptyEl.classList.add('hidden');

    if (data.population) {
        viz.updatePopulation(data.population);
        addLog('predictor', `创世纪：生成 ${data.population.length} 个策略 Genesis: ${data.population.length} strategies spawned`);
    }
    if (data.stats) updateStats(data.stats);
}

function handleGenerationResult(data) {
    const snapshot = data.snapshot;
    const population = data.population;

    if (population) {
        viz.updatePopulation(population);
    }

    if (data.stats) updateStats(data.stats);
    if (data.agents) updateAgents(data.agents);

    if (snapshot) {
        fitnessHistory.push({
            gen: snapshot.generation,
            avg: snapshot.avg_fitness,
            best: snapshot.best_fitness,
            worst: snapshot.worst_fitness,
        });
        drawFitnessChart();

        totalEliminated += snapshot.eliminated_count;
        totalTrades += population ? population.reduce((sum, s) =>
            sum + (s.performance?.trades_count || 0), 0) : 0;

        addLog('judge',
            `第${snapshot.generation}代 Gen${snapshot.generation}: ` +
            `均值avg=${snapshot.avg_fitness.toFixed(4)} ` +
            `最优best=${snapshot.best_fitness.toFixed(4)} ` +
            `淘汰elim=${snapshot.eliminated_count} 变异mut=${snapshot.mutated_count}`
        );
    }

    if (population) updateLeaderboard(population);
    if (population) updateDistributions(population);
}

function handleSelection(data) {
    if (data.eliminated_ids) {
        viz.highlightEliminated(data.eliminated_ids);
        addLog('judge', `淘汰 ${data.eliminated_ids.length} 个策略 Eliminated ${data.eliminated_ids.length} strategies`);
    }
    if (data.elites) {
        addLog('judge', `保留 ${data.elites} 个精英策略 ${data.elites} elite strategies preserved`);
    }
}

function handleA2AMessage(data) {
    const sender = data.sender?.split('-')[0] || 'system';
    const type = data.msg_type || '';

    if (type === 'strategy_batch') {
        const count = data.payload?.candidates?.length || 0;
        addLog('predictor', `生成 ${count} 个新候选策略 Generated ${count} new candidates`);
        document.getElementById('pred-candidates').textContent =
            parseInt(document.getElementById('pred-candidates').textContent) + count;
    } else if (type === 'execution_report') {
        const count = data.payload?.executed_count || 0;
        const results = data.payload?.results || [];
        const portfolio = data.payload?.portfolio;
        addLog('executor', `通过 OnchainOS 执行 ${count} 个策略 Executed ${count} strategies via OnchainOS`);
        // Show top result PnL
        if (results.length > 0) {
            const best = results.reduce((a, b) => (a.pnl_pct > b.pnl_pct ? a : b));
            const worst = results.reduce((a, b) => (a.pnl_pct < b.pnl_pct ? a : b));
            addLog('executor',
                `最优 Best PnL: ${(best.pnl_pct*100).toFixed(2)}% | 最差 Worst: ${(worst.pnl_pct*100).toFixed(2)}%`
            );
        }
        // Update portfolio balance
        if (portfolio) {
            updateBalanceDisplay(portfolio);
        }
    } else if (type === 'evolution_directive') {
        const safe = data.payload?.safe_mode;
        if (safe) {
            document.getElementById('safe-mode-alert').classList.add('active');
            addLog('judge', '安全模式：切换至 OKX Earn SAFE MODE: Switching to OKX Earn');
        } else {
            document.getElementById('safe-mode-alert').classList.remove('active');
        }
    } else if (type === 'safe_mode_trigger') {
        const earn = data.payload?.earn_result || {};
        const src = earn.source || 'simulated';
        addLog('judge', `安全模式触发 Safe Mode! ${data.payload?.reason || ''}`);
        addLog('judge', `OKX Earn ${src === 'okx_demo_trading' ? '[REAL API]' : '[SIM]'}: ${earn.amount || 0} USDT -> ${earn.product || 'savings'}`);
    } else if (type === 'risk_alert') {
        addLog('judge', `风险预警 Risk Alert: ${data.payload?.reason || '未知 Unknown'}`);
    }
}

function handleEvolutionComplete(data) {
    setEvolvingState(false);
    addLog('system',
        `进化完成！共 ${data.total_generations} 代，最终平均适应度：${data.final_stats?.avg_fitness?.toFixed(4) || '--'} ` +
        `Evolution complete! ${data.total_generations} generations. Final avg fitness: ${data.final_stats?.avg_fitness?.toFixed(4) || '--'}`
    );
    // Show evolution report
    if (data.report) {
        showEvolutionReport(data.report);
    }
}

function handleReset() {
    fitnessHistory = [];
    balanceHistory = [];
    geneDriftHistory = [];
    totalEliminated = 0;
    totalTrades = 0;
    drawFitnessChart();
    setEvolvingState(false);
    updateStats({ generation: 0, population_size: 0, avg_fitness: 0, best_fitness: 0 });
    document.getElementById('stat-balance').textContent = '$100,000';
    document.getElementById('stat-pnl').textContent = '0.00%';
    document.getElementById('stat-pnl').className = 'value';
    addLog('system', '系统已重置 System reset');
}

// ─── UI Controls 界面控制 ────────────────────────

function startEvolution() {
    const gens = parseInt(document.getElementById('cfg-generations')?.value || '15');
    sendCommand('start_evolution', { generations: gens });
    setEvolvingState(true);
    addLog('system', `正在启动 ${gens} 代进化… Starting ${gens}-generation evolution...`);
}

function stepEvolution() {
    sendCommand('step_evolution');
    addLog('system', '执行单步进化… Running single evolution step...');
}

function stopEvolution() {
    sendCommand('stop_evolution');
    setEvolvingState(false);
}

function resetEvolution() {
    sendCommand('reset');
    viz.updatePopulation([]);
}

function setEvolvingState(evolving) {
    isEvolving = evolving;
    document.getElementById('btn-start').disabled = evolving;
    document.getElementById('btn-step').disabled = evolving;
    document.getElementById('btn-stop').disabled = !evolving;
    document.getElementById('app').classList.toggle('evolving', evolving);
}

// ─── Stats Display 数据展示 ─────────────────────

function updateStats(stats) {
    document.getElementById('stat-gen').textContent = stats.generation || 0;
    document.getElementById('stat-pop').textContent = stats.population_size || 0;

    const best = stats.best_fitness || 0;
    const bestEl = document.getElementById('stat-best');
    bestEl.textContent = best.toFixed(4);
    bestEl.className = 'value ' + (best > 0 ? 'positive' : best < 0 ? 'negative' : '');

    const avg = stats.avg_fitness || 0;
    const avgEl = document.getElementById('stat-avg');
    avgEl.textContent = avg.toFixed(4);
    avgEl.className = 'value ' + (avg > 0 ? 'positive' : avg < 0 ? 'negative' : '');
}

// 市场体制中英文映射 Market regime bilingual mapping
const regimeLabels = {
    'normal': '正常 NORMAL',
    'trending_up': '上涨趋势 TRENDING UP',
    'trending_down': '下跌趋势 TRENDING DOWN',
    'high_volatility': '高波动 HIGH VOLATILITY',
    'bull_volatile': '牛市波动 BULL VOLATILE',
    'bear_volatile': '熊市波动 BEAR VOLATILE',
    'funding_extreme_positive': '资金费率极端正 FUNDING EXTREME+',
    'funding_extreme_negative': '资金费率极端负 FUNDING EXTREME-',
    'range_bound': '横盘震荡 RANGE BOUND',
};

function updateMarketDisplay(data) {
    if (!data) return;

    const regime = data.regime || 'normal';
    const regimeEl = document.getElementById('stat-regime');
    regimeEl.textContent = regimeLabels[regime] || regime.replace(/_/g, ' ').toUpperCase();
    regimeEl.className = 'regime-badge ' + regime;

    if (data.price) {
        document.getElementById('okx-market').textContent =
            '$' + parseFloat(data.price).toLocaleString();
    }
    if (data.funding_rate !== undefined) {
        const fr = (data.funding_rate * 100).toFixed(4);
        document.getElementById('okx-funding').textContent = fr + '%';
    }

    // Data source indicator
    const sourceEl = document.getElementById('okx-source');
    if (sourceEl) {
        const source = data.source || 'simulated';
        if (source === 'mcp_agent_trade_kit') {
            sourceEl.innerHTML = '<span class="source-badge live">MCP AGENT TRADE KIT</span>';
        } else if (source === 'okx_live') {
            sourceEl.innerHTML = '<span class="source-badge live">OKX LIVE API</span>';
        } else {
            sourceEl.innerHTML = '<span class="source-badge simulated">SIMULATED</span>';
        }
    }

    // DEX best chain
    if (data.cross_chain && data.cross_chain.best_route) {
        const el = document.getElementById('dex-best-chain');
        if (el) el.textContent = data.cross_chain.best_route;
    }
}

function updateAgents(agents) {
    if (agents.predictor) {
        document.getElementById('pred-msgs').textContent =
            agents.predictor.messages_processed || 0;
        document.getElementById('pred-status').textContent = isEvolving ? '生成中 Generating' : '空闲 Idle';
    }
    if (agents.executor) {
        document.getElementById('exec-msgs').textContent =
            agents.executor.messages_processed || 0;
        document.getElementById('exec-trades').textContent = totalTrades;
        document.getElementById('exec-status').textContent = isEvolving ? '执行中 Executing' : '空闲 Idle';
        // Update balance from executor status
        if (agents.executor.portfolio) {
            updateBalanceDisplay(agents.executor.portfolio);
        }
        if (agents.executor.balance_history) {
            balanceHistory = agents.executor.balance_history;
        }
    }
    if (agents.judge) {
        document.getElementById('judge-msgs').textContent =
            agents.judge.messages_processed || 0;
        document.getElementById('judge-eliminated').textContent = totalEliminated;
        document.getElementById('judge-status').textContent = isEvolving ? '评估中 Evaluating' : '空闲 Idle';
    }
}

function updateLeaderboard(population) {
    const sorted = [...population].sort((a, b) =>
        (b.fitness_score || 0) - (a.fitness_score || 0));
    const top5 = sorted.slice(0, 5);

    // 策略类型中英文映射 Strategy type bilingual mapping
    const typeLabelsBI = {
        'funding_arb': '套利 arb',
        'grid': '网格 grid',
        'momentum': '动量 mom',
        'mean_reversion': '回归 mr',
    };
    const dirLabelsBI = {
        'long': '多 long',
        'short': '空 short',
        'neutral': '中性 neutral',
    };

    const html = top5.map((s, i) => {
        const fitness = (s.fitness_score || 0).toFixed(4);
        const color = s.fitness_score > 0.02 ? '#10b981' :
                      s.fitness_score > 0 ? '#34d399' : '#ef4444';
        const type = s.genes?.strategy_type || s.strategy_type || '--';
        const dir = s.genes?.direction || s.direction || '--';
        const typeBI = typeLabelsBI[type] || type;
        const dirBI = dirLabelsBI[dir] || dir;
        const bal = s.virtual_balance || 10000;
        const balPnl = s.balance_pnl_pct || 0;
        const balColor = balPnl > 0 ? '#10b981' : balPnl < 0 ? '#ef4444' : '#94a3b8';
        return `<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:11px;align-items:center">
            <span style="color:var(--text-muted)">#${i + 1}</span>
            <span style="color:var(--text-secondary);min-width:50px">${s.id?.slice(0,6)}</span>
            <span style="color:var(--text-muted);font-size:10px">${typeBI}</span>
            <span style="color:${balColor};font-weight:600;font-size:10px">$${Math.round(bal).toLocaleString()}</span>
            <span style="color:${balColor};font-size:10px">${balPnl > 0 ? '+' : ''}${balPnl.toFixed(1)}%</span>
        </div>`;
    }).join('');

    document.getElementById('leaderboard').innerHTML = html;
}

function updateDistributions(population) {
    const dirs = { long: 0, short: 0, neutral: 0 };
    const types = { funding_arb: 0, grid: 0, momentum: 0, mean_reversion: 0 };
    let totalLeverage = 0;
    let totalHedge = 0;

    for (const s of population) {
        const genes = s.genes || s;
        const dir = genes.direction || 'neutral';
        const type = genes.strategy_type || 'momentum';
        dirs[dir] = (dirs[dir] || 0) + 1;
        types[type] = (types[type] || 0) + 1;
        totalLeverage += genes.leverage || 1;
        totalHedge += genes.hedge_ratio || 0;
    }

    const n = population.length || 1;

    // 方向分布条 Direction distribution bar
    const dirBar = document.getElementById('dir-dist');
    const dirLabels = { long: '多 L', short: '空 S', neutral: '中 N' };
    dirBar.innerHTML = Object.entries(dirs).map(([k, v]) => {
        const pct = (v / n * 100).toFixed(0);
        return `<div class="segment ${k}" style="width:${pct}%">${pct > 10 ? dirLabels[k] + ' ' + pct + '%' : ''}</div>`;
    }).join('');

    // 类型分布条 Type distribution bar
    const typeBar = document.getElementById('type-dist');
    const typeLabels = { funding_arb: '套利 Arb', grid: '网格 Grid', momentum: '动量 Mom', mean_reversion: '回归 MR' };
    typeBar.innerHTML = Object.entries(types).map(([k, v]) => {
        const pct = (v / n * 100).toFixed(0);
        return `<div class="segment ${k}" style="width:${Math.max(pct, 1)}%">${pct > 12 ? typeLabels[k] + ' ' + pct + '%' : ''}</div>`;
    }).join('');

    document.getElementById('avg-leverage').textContent =
        (totalLeverage / n).toFixed(1) + 'x';
    document.getElementById('avg-hedge').textContent =
        (totalHedge / n * 100).toFixed(0) + '%';

    // Draw best strategy gene radar
    const best = [...population].sort((a, b) => (b.fitness_score || 0) - (a.fitness_score || 0))[0];
    if (best) drawGeneRadar(best);
}

function drawGeneRadar(strategy) {
    const canvas = document.getElementById('gene-radar');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const cx = w / 2, cy = h / 2 + 5;
    const R = Math.min(w, h) * 0.35;

    ctx.clearRect(0, 0, w, h);

    const genes = strategy.genes || strategy;
    // Normalize each gene to 0-1 scale
    const axes = [
        { label: '杠杆 Lev', value: Math.min((genes.leverage || 1) / 10, 1) },
        { label: '入场 Entry', value: Math.min((genes.entry_threshold || 0.5) / 1, 1) },
        { label: '止盈 TP', value: Math.min((genes.take_profit_pct || 0.1) / 0.3, 1) },
        { label: '对冲 Hedge', value: genes.hedge_ratio || 0 },
        { label: '止损 SL', value: Math.min((genes.stop_loss_pct || 0.05) / 0.15, 1) },
        { label: '出场 Exit', value: Math.min((genes.exit_threshold || 0.3) / 0.6, 1) },
    ];

    const n = axes.length;
    const angleStep = (Math.PI * 2) / n;

    // Draw grid rings
    for (let ring = 0.25; ring <= 1; ring += 0.25) {
        ctx.beginPath();
        for (let i = 0; i <= n; i++) {
            const angle = i * angleStep - Math.PI / 2;
            const x = cx + Math.cos(angle) * R * ring;
            const y = cy + Math.sin(angle) * R * ring;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = '#1e293b';
        ctx.lineWidth = 0.5;
        ctx.stroke();
    }

    // Draw axis lines
    for (let i = 0; i < n; i++) {
        const angle = i * angleStep - Math.PI / 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(angle) * R, cy + Math.sin(angle) * R);
        ctx.strokeStyle = '#2a3a4e';
        ctx.lineWidth = 0.5;
        ctx.stroke();
    }

    // Draw data polygon (filled)
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const val = axes[i].value;
        const x = cx + Math.cos(angle) * R * val;
        const y = cy + Math.sin(angle) * R * val;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(16, 185, 129, 0.15)';
    ctx.fill();
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw data points
    for (let i = 0; i < n; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const val = axes[i].value;
        const x = cx + Math.cos(angle) * R * val;
        const y = cy + Math.sin(angle) * R * val;
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#10b981';
        ctx.fill();
    }

    // Labels
    ctx.fillStyle = '#94a3b8';
    ctx.font = '9px Inter';
    ctx.textAlign = 'center';
    for (let i = 0; i < n; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const lx = cx + Math.cos(angle) * (R + 18);
        const ly = cy + Math.sin(angle) * (R + 18);
        ctx.fillText(axes[i].label, lx, ly + 3);
    }
}

// ─── Fitness Timeline Chart 适应度时间线图表 ─────

let chartCtx = null;

function initFitnessChart() {
    const canvas = document.getElementById('fitness-timeline');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = 100;
    chartCtx = canvas.getContext('2d');
    drawFitnessChart();
}

function drawFitnessChart() {
    if (!chartCtx) return;
    const canvas = chartCtx.canvas;
    const w = canvas.width;
    const h = canvas.height;
    const padding = { top: 10, right: 10, bottom: 20, left: 40 };

    chartCtx.clearRect(0, 0, w, h);

    if (fitnessHistory.length < 2) {
        chartCtx.fillStyle = '#64748b';
        chartCtx.font = '12px Inter';
        chartCtx.textAlign = 'center';
        chartCtx.fillText('等待进化数据… Waiting for evolution data...', w / 2, h / 2);
        return;
    }

    const data = fitnessHistory;
    const allValues = data.flatMap(d => [d.best, d.avg, d.worst]);
    const minY = Math.min(...allValues) - 0.005;
    const maxY = Math.max(...allValues) + 0.005;
    const rangeY = maxY - minY || 0.01;

    const plotW = w - padding.left - padding.right;
    const plotH = h - padding.top - padding.bottom;

    const xScale = (i) => padding.left + (i / (data.length - 1)) * plotW;
    const yScale = (v) => padding.top + plotH - ((v - minY) / rangeY) * plotH;

    // Zero line
    if (minY < 0 && maxY > 0) {
        const zeroY = yScale(0);
        chartCtx.strokeStyle = '#2a3a4e';
        chartCtx.lineWidth = 1;
        chartCtx.setLineDash([4, 4]);
        chartCtx.beginPath();
        chartCtx.moveTo(padding.left, zeroY);
        chartCtx.lineTo(w - padding.right, zeroY);
        chartCtx.stroke();
        chartCtx.setLineDash([]);
    }

    // Best-worst range area
    chartCtx.fillStyle = 'rgba(59, 130, 246, 0.08)';
    chartCtx.beginPath();
    chartCtx.moveTo(xScale(0), yScale(data[0].best));
    for (let i = 1; i < data.length; i++) {
        chartCtx.lineTo(xScale(i), yScale(data[i].best));
    }
    for (let i = data.length - 1; i >= 0; i--) {
        chartCtx.lineTo(xScale(i), yScale(data[i].worst));
    }
    chartCtx.closePath();
    chartCtx.fill();

    // Lines
    const drawLine = (key, color, width) => {
        chartCtx.strokeStyle = color;
        chartCtx.lineWidth = width;
        chartCtx.beginPath();
        for (let i = 0; i < data.length; i++) {
            const x = xScale(i);
            const y = yScale(data[i][key]);
            if (i === 0) chartCtx.moveTo(x, y);
            else chartCtx.lineTo(x, y);
        }
        chartCtx.stroke();
    };

    drawLine('best', '#10b981', 2);
    drawLine('avg', '#3b82f6', 2);
    drawLine('worst', '#ef4444', 1);

    // Y-axis labels
    chartCtx.fillStyle = '#64748b';
    chartCtx.font = '10px JetBrains Mono';
    chartCtx.textAlign = 'right';
    chartCtx.fillText(maxY.toFixed(3), padding.left - 4, padding.top + 10);
    chartCtx.fillText(minY.toFixed(3), padding.left - 4, h - padding.bottom);

    // X-axis labels
    chartCtx.textAlign = 'center';
    chartCtx.fillText('0', padding.left, h - 4);
    chartCtx.fillText(String(data.length - 1), w - padding.right, h - 4);

    // Legend 图例
    chartCtx.textAlign = 'right';
    chartCtx.font = '10px Inter';
    const lx = w - padding.right;
    chartCtx.fillStyle = '#ef4444';
    chartCtx.fillText('最差 Worst', lx, padding.top + 10);
    chartCtx.fillStyle = '#3b82f6';
    chartCtx.fillText('均值 Avg', lx - 80, padding.top + 10);
    chartCtx.fillStyle = '#10b981';
    chartCtx.fillText('最优 Best', lx - 150, padding.top + 10);
}

// ─── Log 日志 ────────────────────────────────────

function addLog(agent, message) {
    const container = document.getElementById('log-entries');
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', { hour12: false });

    // Agent 中英文映射
    const agentLabels = {
        'system': '系统 system',
        'predictor': '预测 predictor',
        'executor': '执行 executor',
        'judge': '裁判 judge',
    };

    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <span class="time">${time}</span>
        <span class="agent ${agent}">${agentLabels[agent] || agent}</span>
        <span class="msg">${message}</span>
    `;

    container.insertBefore(entry, container.firstChild);

    while (container.children.length > 100) {
        container.removeChild(container.lastChild);
    }
}

// ─── Portfolio Balance 资金余额 ───────────────

function updateBalanceDisplay(portfolio) {
    if (!portfolio) return;

    const balanceEl = document.getElementById('stat-balance');
    const pnlEl = document.getElementById('stat-pnl');

    if (portfolio.balance) {
        balanceEl.textContent = '$' + Math.round(portfolio.balance).toLocaleString();
        const returnPct = portfolio.cumulative_return_pct || 0;
        pnlEl.textContent = (returnPct > 0 ? '+' : '') + returnPct.toFixed(2) + '%';
        pnlEl.className = 'value ' + (returnPct > 0 ? 'positive' : returnPct < 0 ? 'negative' : '');

        // Color balance based on profit/loss
        if (portfolio.balance > (portfolio.initial_balance || 100000)) {
            balanceEl.style.color = 'var(--accent-green)';
        } else if (portfolio.balance < (portfolio.initial_balance || 100000)) {
            balanceEl.style.color = 'var(--accent-red)';
        } else {
            balanceEl.style.color = 'var(--accent-yellow)';
        }
    }
}

// ─── Settings Panel 设置面板 ──────────────────

function toggleSettings() {
    switchTab('tab-config');
}

// ─── Tab System ──────────────────────────────────

function switchTab(tabId) {
    // Deactivate all tabs
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    // Activate selected
    const tab = document.getElementById(tabId);
    if (tab) tab.classList.add('active');
    // Activate matching button
    const btns = document.querySelectorAll('.tab-btn');
    const tabNames = ['tab-agents', 'tab-okx', 'tab-about', 'tab-config'];
    const idx = tabNames.indexOf(tabId);
    if (idx >= 0 && btns[idx]) btns[idx].classList.add('active');
}

function applySettings() {
    const params = {
        population_size: parseInt(document.getElementById('cfg-pop-size').value),
        mutation_rate: parseInt(document.getElementById('cfg-mutation').value) / 100,
        selection_pressure: parseInt(document.getElementById('cfg-selection').value) / 100,
        max_generations: parseInt(document.getElementById('cfg-generations').value),
    };
    sendCommand('update_config', { params });

    // Switch execution mode
    const execMode = document.getElementById('cfg-exec-mode').value;
    sendCommand('switch_mode', { mode: execMode });

    addLog('system',
        `参数已更新 Config updated: 种群=${params.population_size} 模式=${execMode}`
    );
}

function updateExecModeDisplay(mode, canTrade) {
    const el = document.getElementById('okx-exec-mode');
    if (!el) return;
    if (mode === 'demo_api' && canTrade) {
        el.innerHTML = '<span class="source-badge live">OKX DEMO</span>';
    } else if (mode === 'demo_api') {
        el.innerHTML = '<span class="source-badge simulated">NO API KEY</span>';
    } else {
        el.innerHTML = '<span class="source-badge simulated">SIMULATION</span>';
    }
    // Sync select
    const sel = document.getElementById('cfg-exec-mode');
    if (sel) sel.value = mode;
}

async function fetchAccountInfo() {
    try {
        const resp = await fetch('/api/account');
        const data = await resp.json();
        if (data.balance) {
            const eq = data.balance.total_equity;
            document.getElementById('okx-balance').textContent =
                eq > 0 ? '$' + eq.toLocaleString(undefined, {maximumFractionDigits:2}) : '--';
        }
        document.getElementById('okx-positions').textContent =
            data.positions ? data.positions.length : '0';
        updateExecModeDisplay(data.execution_mode, data.can_trade);
    } catch(e) { /* ignore */ }
}

// ─── Export 导出 ────────────────────────────────

function exportStrategies() {
    sendCommand('export_strategies', { top_n: 5 });
    addLog('system', '正在导出 Top5 策略… Exporting top 5 strategies...');
}

function handleEvent_extended(event, data) {
    if (event === 'export_result') {
        showExportModal(data);
    } else if (event === 'config_updated') {
        addLog('system', '服务端配置已同步 Server config synced');
    } else if (event === 'mode_changed') {
        updateExecModeDisplay(data.execution_mode, data.can_trade);
        const modeLabel = data.execution_mode === 'demo_api' ? 'OKX Demo Trading' : 'Simulation';
        addLog('system', `执行模式切换 Mode: ${modeLabel} | API Keys: ${data.has_api_keys ? 'Yes' : 'No'}`);
    } else if (event === 'init') {
        if (data.config) {
            updateExecModeDisplay(data.config.execution_mode, data.config.can_trade);
        }
        fetchAccountInfo();
        fetchMCPStats();
    } else if (event === 'deploy_result') {
        showDeployResult(data);
    } else if (event === 'generation_result') {
        // Update gene drift chart
        if (data.gene_drift) {
            geneDriftHistory.push(data.gene_drift);
            drawGeneDriftChart();
        }
    } else if (event === 'gene_drift_data') {
        geneDriftHistory = data.drift || [];
        drawGeneDriftChart();
    }
}

// Extend existing handleEvent
const _origHandleEvent = handleEvent;
handleEvent = function(event, data) {
    _origHandleEvent(event, data);
    handleEvent_extended(event, data);
};

function showExportModal(data) {
    const overlay = document.createElement('div');
    overlay.className = 'export-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const json = JSON.stringify(data, null, 2);
    overlay.innerHTML = `
        <div class="export-modal">
            <h3>策略导出 Strategy Export (Top ${data.strategies?.length || 0})</h3>
            <pre id="export-json">${escapeHtml(json)}</pre>
            <div class="btn-row">
                <button class="btn btn-primary" onclick="copyExport()">复制 Copy JSON</button>
                <button class="btn btn-secondary" onclick="downloadExport()">下载 Download</button>
                <button class="btn btn-secondary" onclick="this.closest('.export-overlay').remove()">关闭 Close</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    // Store data for download
    window._exportData = json;
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function copyExport() {
    if (window._exportData) {
        navigator.clipboard.writeText(window._exportData).then(() => {
            addLog('system', '已复制到剪贴板 Copied to clipboard');
        });
    }
}

function downloadExport() {
    if (window._exportData) {
        const blob = new Blob([window._exportData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `genefi_strategies_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        addLog('system', '策略文件已下载 Strategy file downloaded');
    }
}

// ─── Backtest 回测 ──────────────────────────────

async function runBacktest() {
    addLog('system', '正在运行回测对比… Running backtest comparison...');
    try {
        const resp = await fetch('/api/backtest');
        const data = await resp.json();
        if (data.error) {
            addLog('system', `回测失败 Backtest error: ${data.error}`);
            return;
        }
        showBacktestResult(data);
    } catch (e) {
        addLog('system', `回测请求失败 Backtest request failed: ${e.message}`);
    }
}

function showBacktestResult(data) {
    const overlay = document.createElement('div');
    overlay.className = 'export-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const gain = data.improvement || {};
    const avgGain = (gain.avg_fitness_gain || 0);
    const bestGain = (gain.best_fitness_gain || 0);
    const avgColor = avgGain > 0 ? '#10b981' : '#ef4444';
    const bestColor = bestGain > 0 ? '#10b981' : '#ef4444';

    overlay.innerHTML = `
        <div class="export-modal">
            <h3>回测对比 Backtest: Evolution vs Random</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0">
                <div style="text-align:center">
                    <div style="font-size:12px;color:var(--text-muted)">平均适应度增益 Avg Fitness Gain</div>
                    <div style="font-size:28px;font-weight:700;color:${avgColor}">${avgGain > 0 ? '+' : ''}${avgGain.toFixed(4)}</div>
                </div>
                <div style="text-align:center">
                    <div style="font-size:12px;color:var(--text-muted)">最优适应度增益 Best Fitness Gain</div>
                    <div style="font-size:28px;font-weight:700;color:${bestColor}">${bestGain > 0 ? '+' : ''}${bestGain.toFixed(4)}</div>
                </div>
            </div>
            <canvas id="backtest-chart" width="540" height="200"></canvas>
            <div class="btn-row">
                <button class="btn btn-secondary" onclick="this.closest('.export-overlay').remove()">关闭 Close</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    // Draw backtest chart
    setTimeout(() => drawBacktestChart(data), 100);
}

function drawBacktestChart(data) {
    const canvas = document.getElementById('backtest-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const pad = { top: 20, right: 20, bottom: 30, left: 50 };

    ctx.clearRect(0, 0, w, h);

    const evolved = data.evolved?.avg || [];
    const baseline = data.random_baseline?.avg || [];
    const n = Math.max(evolved.length, baseline.length);
    if (n < 2) return;

    const allVals = [...evolved, ...baseline];
    const minY = Math.min(...allVals) - 0.005;
    const maxY = Math.max(...allVals) + 0.005;
    const rangeY = maxY - minY || 0.01;

    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;
    const xScale = (i) => pad.left + (i / (n - 1)) * plotW;
    const yScale = (v) => pad.top + plotH - ((v - minY) / rangeY) * plotH;

    // Grid
    ctx.strokeStyle = '#2a3a4e';
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 4; i++) {
        const y = pad.top + (plotH / 3) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(w - pad.right, y);
        ctx.stroke();
    }

    // Evolved line (green)
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.beginPath();
    evolved.forEach((v, i) => {
        const x = xScale(i), y = yScale(v);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Baseline line (red dashed)
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    baseline.forEach((v, i) => {
        const x = xScale(i), y = yScale(v);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    // Labels
    ctx.fillStyle = '#64748b';
    ctx.font = '10px Inter';
    ctx.textAlign = 'left';
    ctx.fillText(`${maxY.toFixed(3)}`, 2, pad.top + 10);
    ctx.fillText(`${minY.toFixed(3)}`, 2, h - pad.bottom);

    // Legend
    ctx.fillStyle = '#10b981';
    ctx.fillRect(pad.left, h - 15, 12, 3);
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('进化 Evolved', pad.left + 16, h - 10);
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(pad.left + 120, h - 15, 12, 3);
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('随机 Random', pad.left + 136, h - 10);
}

// ─── Evolution Report 进化报告 ────────────────────

// ─── Deploy Strategy 部署策略 ─────────────────────

function deployBestStrategy(strategyId) {
    sendCommand('deploy_strategy', { strategy_id: strategyId || null });
    addLog('system', '正在部署最优策略到 OKX… Deploying best strategy to OKX...');
}

function showDeployResult(data) {
    const overlay = document.createElement('div');
    overlay.className = 'export-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const strategy = data.strategy || {};
    const actions = data.actions || [];
    const sources = data.api_sources || [];
    const isReal = sources.includes('okx_demo_trading');

    const actionsHtml = actions.map(a => {
        const src = a.result?.source || 'unknown';
        const srcBadge = src === 'okx_demo_trading'
            ? '<span class="source-badge live">OKX REAL</span>'
            : '<span class="source-badge simulated">SIMULATED</span>';
        return `<div style="background:var(--bg-primary);border-radius:6px;padding:8px;margin:4px 0;font-size:11px">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <strong style="color:var(--accent-cyan)">${a.type}</strong>
                ${srcBadge}
            </div>
            <div style="color:var(--text-secondary);font-family:'JetBrains Mono',monospace;font-size:10px">
                ${a.result?.order_id || a.result?.bot_id || a.result?.action || '--'}
                ${a.result?.symbol ? ' | ' + a.result.symbol : ''}
                ${a.result?.side ? ' | ' + a.result.side : ''}
                ${a.result?.leverage ? ' | ' + a.result.leverage + 'x' : ''}
            </div>
        </div>`;
    }).join('');

    overlay.innerHTML = `
        <div class="export-modal" style="max-width:550px">
            <h3 style="color:var(--accent-yellow)">策略部署 Strategy Deployment</h3>
            <div style="background:var(--bg-primary);border-radius:8px;padding:12px;margin:12px 0">
                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px">
                    <span style="color:var(--text-muted)">策略 Strategy</span>
                    <strong>${strategy.id?.slice(0,12) || '--'}</strong>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px">
                    <span style="color:var(--text-muted)">类型 Type</span>
                    <strong>${strategy.strategy_type}/${strategy.direction}</strong>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px">
                    <span style="color:var(--text-muted)">适应度 Fitness</span>
                    <strong style="color:var(--accent-green)">${strategy.fitness_score?.toFixed(4)}</strong>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12px">
                    <span style="color:var(--text-muted)">杠杆 Leverage</span>
                    <strong style="color:var(--accent-yellow)">${strategy.leverage?.toFixed(1)}x</strong>
                </div>
            </div>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px">执行动作 Actions (${actions.length})</div>
            ${actionsHtml}
            <div class="btn-row">
                <button class="btn btn-secondary" onclick="this.closest('.export-overlay').remove()">关闭 Close</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    addLog('system',
        `策略已部署 Strategy deployed: ${strategy.strategy_type}/${strategy.direction} ` +
        `via ${isReal ? 'OKX Demo Trading API' : 'Simulation'} | ${actions.length} actions`
    );
    fetchAccountInfo();
}

// ─── Gene Drift 基因漂变 ────────────────────────────

let geneDriftHistory = [];

function drawGeneDriftChart() {
    const canvas = document.getElementById('gene-drift-canvas');
    if (!canvas || geneDriftHistory.length < 2) return;

    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const pad = { top: 8, right: 8, bottom: 16, left: 30 };
    const data = geneDriftHistory;
    const n = data.length;

    ctx.clearRect(0, 0, w, h);

    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;
    const xScale = (i) => pad.left + (i / (n - 1)) * plotW;

    // Gene tracks to display (normalized to 0-1 range)
    const genes = [
        { key: 'leverage', color: '#f59e0b', label: '杠杆 Lev', min: 1, max: 20 },
        { key: 'hedge_ratio', color: '#06b6d4', label: '对冲 Hedge', min: 0, max: 1 },
        { key: 'entry_threshold', color: '#10b981', label: '入场 Entry', min: 0, max: 0.1 },
        { key: 'stop_loss_pct', color: '#ef4444', label: '止损 SL', min: 0.01, max: 0.15 },
        { key: 'take_profit_pct', color: '#8b5cf6', label: '止盈 TP', min: 0.02, max: 0.3 },
    ];

    // Draw each gene line
    genes.forEach(gene => {
        const normalize = (v) => {
            const range = gene.max - gene.min || 1;
            return Math.max(0, Math.min(1, (v - gene.min) / range));
        };
        const yScale = (v) => pad.top + plotH - normalize(v) * plotH;

        ctx.strokeStyle = gene.color;
        ctx.lineWidth = 1.5;
        ctx.globalAlpha = 0.8;
        ctx.beginPath();
        data.forEach((d, i) => {
            const x = xScale(i);
            const y = yScale(d[gene.key] || 0);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.globalAlpha = 1;
    });

    // X axis
    ctx.fillStyle = '#64748b';
    ctx.font = '9px JetBrains Mono';
    ctx.textAlign = 'center';
    ctx.fillText('Gen 0', pad.left, h - 2);
    ctx.fillText(`Gen ${n - 1}`, w - pad.right, h - 2);

    // Legend
    const legendEl = document.getElementById('drift-legend');
    if (legendEl) {
        legendEl.innerHTML = genes.map(g =>
            `<span style="color:${g.color};margin-right:6px">\u25CF ${g.label}</span>`
        ).join('');
    }
}

// ─── Investment Simulator 投资模拟器 ──────────────

async function runInvestmentSimulator() {
    const capital = parseFloat(document.getElementById('cfg-capital')?.value || '10000');
    addLog('system', `正在模拟 $${capital.toLocaleString()} 投资… Simulating $${capital.toLocaleString()} investment...`);

    try {
        const resp = await fetch(`/api/simulate_investment?capital=${capital}&days=7`);
        const data = await resp.json();
        if (data.error) {
            addLog('system', `模拟失败 Error: ${data.error}`);
            return;
        }
        showInvestmentResult(data);
    } catch (e) {
        addLog('system', `请求失败 Request failed: ${e.message}`);
    }
}

function showInvestmentResult(data) {
    const overlay = document.createElement('div');
    overlay.className = 'export-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const input = data.input;
    const evolved = data.evolved_portfolio;
    const random = data.random_baseline;
    const alpha = data.alpha;
    const btc = data.btc_price;

    const profitColor = evolved.total_return_pct > 0 ? '#10b981' : '#ef4444';
    const profitSign = evolved.total_return_pct > 0 ? '+' : '';
    const alphaColor = alpha.evolved_vs_random > 0 ? '#10b981' : '#ef4444';

    overlay.innerHTML = `
        <div class="export-modal" style="max-width:700px">
            <h3 style="color:var(--accent-yellow)">&#128176; 投资模拟结果 Investment Simulation</h3>

            <div style="text-align:center;margin:16px 0;padding:16px;background:var(--bg-primary);border-radius:12px">
                <div style="font-size:12px;color:var(--text-muted)">投入本金 Initial Capital</div>
                <div style="font-size:20px;color:var(--text-secondary);margin:4px 0">$${input.capital.toLocaleString()}</div>
                <div style="font-size:14px;color:var(--text-muted);margin:8px 0">↓ ${data.period.hours}小时 ${data.period.hours}H (${data.period.candles_count} 根真实OKX K线 real candles) ↓</div>
                <div style="font-size:14px;color:var(--text-muted)">BTC ${btc.change_pct > 0 ? '↑' : '↓'} ${btc.change_pct}% ($${btc.start.toLocaleString()} → $${btc.end.toLocaleString()})</div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin:16px 0">
                <div style="background:var(--bg-primary);border-radius:10px;padding:14px;text-align:center;border:2px solid ${profitColor}">
                    <div style="font-size:11px;color:var(--text-muted)">进化策略 Evolved</div>
                    <div style="font-size:28px;font-weight:700;color:${profitColor}">$${evolved.final_capital.toLocaleString()}</div>
                    <div style="font-size:14px;color:${profitColor}">${profitSign}${evolved.total_return_pct}%</div>
                </div>
                <div style="background:var(--bg-primary);border-radius:10px;padding:14px;text-align:center">
                    <div style="font-size:11px;color:var(--text-muted)">随机策略 Random</div>
                    <div style="font-size:28px;font-weight:700;color:var(--text-secondary)">$${random.final_capital.toLocaleString()}</div>
                    <div style="font-size:14px;color:var(--text-secondary)">${random.total_return_pct > 0 ? '+' : ''}${random.total_return_pct}%</div>
                </div>
                <div style="background:var(--bg-primary);border-radius:10px;padding:14px;text-align:center;border:2px solid ${alphaColor}">
                    <div style="font-size:11px;color:var(--text-muted)">Alpha 超额收益</div>
                    <div style="font-size:28px;font-weight:700;color:${alphaColor}">${alpha.evolved_vs_random > 0 ? '+' : ''}${alpha.evolved_vs_random}%</div>
                    <div style="font-size:14px;color:${alphaColor}">$${alpha.extra_profit > 0 ? '+' : ''}${alpha.extra_profit.toLocaleString()}</div>
                </div>
            </div>

            <div style="background:var(--bg-primary);border-radius:8px;padding:12px;margin:12px 0">
                <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px">资金曲线 Capital Curve (真实OKX K线回测 Real OKX Candle Backtest)</div>
                <canvas id="investment-chart" width="640" height="200"></canvas>
            </div>

            <div style="display:flex;gap:16px;font-size:11px;color:var(--text-muted);margin:8px 0">
                <span>最高 Peak: $${evolved.max_capital.toLocaleString()}</span>
                <span>最低 Low: $${evolved.min_capital.toLocaleString()}</span>
                <span>最大回撤 MaxDD: ${evolved.max_drawdown_pct}%</span>
            </div>

            <div style="font-size:10px;color:var(--text-muted);margin-top:8px;padding:8px;background:rgba(245,158,11,0.1);border-radius:6px;border:1px solid rgba(245,158,11,0.2)">
                ⚠️ 模拟结果基于历史数据，不代表未来收益。Strategy backtested on historical OKX data. Past performance does not guarantee future returns.
            </div>

            <div class="btn-row">
                <button class="btn btn-primary" onclick="deployBestStrategy();this.closest('.export-overlay').remove()" style="background:linear-gradient(135deg,var(--accent-yellow),#d97706)">&#9889; 部署最优策略 Deploy</button>
                <button class="btn btn-secondary" onclick="exportStrategies()">导出策略 Export</button>
                <button class="btn btn-secondary" onclick="this.closest('.export-overlay').remove()">关闭 Close</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    // Draw capital curve
    setTimeout(() => drawInvestmentChart(data), 100);

    addLog('system',
        `模拟完成 Simulation done: $${input.capital.toLocaleString()} → $${evolved.final_capital.toLocaleString()} (${profitSign}${evolved.total_return_pct}%) | Alpha: ${alpha.evolved_vs_random}%`
    );
}

function drawInvestmentChart(data) {
    const canvas = document.getElementById('investment-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const pad = { top: 20, right: 20, bottom: 25, left: 60 };

    ctx.clearRect(0, 0, w, h);

    const curve = data.evolved_portfolio.capital_curve;
    if (!curve || curve.length < 2) return;

    const n = curve.length;
    const capital = data.input.capital;
    const minY = Math.min(...curve, capital) * 0.98;
    const maxY = Math.max(...curve, capital) * 1.02;
    const rangeY = maxY - minY || 1;

    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;
    const xScale = (i) => pad.left + (i / (n - 1)) * plotW;
    const yScale = (v) => pad.top + plotH - ((v - minY) / rangeY) * plotH;

    // Grid lines
    ctx.strokeStyle = '#1a2332';
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 4; i++) {
        const y = pad.top + (plotH / 3) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(w - pad.right, y);
        ctx.stroke();
    }

    // Initial capital line (dashed)
    const capitalY = yScale(capital);
    ctx.strokeStyle = '#64748b';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pad.left, capitalY);
    ctx.lineTo(w - pad.right, capitalY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#64748b';
    ctx.font = '10px Inter';
    ctx.textAlign = 'left';
    ctx.fillText('本金 Capital', pad.left + 4, capitalY - 4);

    // Fill area under/over capital line
    ctx.beginPath();
    ctx.moveTo(xScale(0), yScale(curve[0]));
    for (let i = 1; i < n; i++) {
        ctx.lineTo(xScale(i), yScale(curve[i]));
    }
    ctx.lineTo(xScale(n - 1), capitalY);
    ctx.lineTo(xScale(0), capitalY);
    ctx.closePath();
    const finalAbove = curve[curve.length - 1] > capital;
    ctx.fillStyle = finalAbove ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)';
    ctx.fill();

    // Capital curve line
    ctx.strokeStyle = finalAbove ? '#10b981' : '#ef4444';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    curve.forEach((v, i) => {
        const x = xScale(i), y = yScale(v);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    // End point dot
    const lastX = xScale(n - 1);
    const lastY = yScale(curve[n - 1]);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
    ctx.fillStyle = finalAbove ? '#10b981' : '#ef4444';
    ctx.fill();

    // Y axis labels
    ctx.fillStyle = '#64748b';
    ctx.font = '10px JetBrains Mono';
    ctx.textAlign = 'right';
    ctx.fillText('$' + Math.round(maxY).toLocaleString(), pad.left - 4, pad.top + 10);
    ctx.fillText('$' + Math.round(minY).toLocaleString(), pad.left - 4, h - pad.bottom);

    // End value label
    ctx.fillStyle = finalAbove ? '#10b981' : '#ef4444';
    ctx.font = '12px Inter';
    ctx.fontWeight = '700';
    ctx.textAlign = 'left';
    ctx.fillText('$' + Math.round(curve[n - 1]).toLocaleString(), lastX + 8, lastY + 4);
}

function showEvolutionReport(report) {
    const overlay = document.createElement('div');
    overlay.className = 'export-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const impColor = report.improvement_over_random > 0 ? '#10b981' : '#ef4444';
    const impSign = report.improvement_over_random > 0 ? '+' : '';
    const tools = (report.okx_tools_used || []).map(t => {
        const labels = {
            'ai_skills_market_data': 'AI Skills 行情',
            'place_futures_order': '合约下单 Futures',
            'create_grid_bot': '网格机器人 Grid Bot',
            'cross_chain_liquidity_router': '跨链路由 Cross-Chain',
        };
        return labels[t] || t;
    }).join(', ');

    const modeLabel = report.execution_mode === 'demo_api' ? 'OKX Demo Trading 模拟盘' : 'Simulation 本地模拟';
    const sourceLabel = report.market_source === 'okx_live' ? 'OKX 真实行情 Live API' : '模拟数据 Simulated';

    overlay.innerHTML = `
        <div class="export-modal" style="max-width:700px">
            <h3>进化报告 Evolution Report</h3>

            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin:16px 0">
                <div style="background:var(--bg-primary);border-radius:8px;padding:12px;text-align:center">
                    <div style="font-size:11px;color:var(--text-muted)">进化代数 Generations</div>
                    <div style="font-size:24px;font-weight:700;color:var(--accent-cyan)">${report.generations_run}</div>
                </div>
                <div style="background:var(--bg-primary);border-radius:8px;padding:12px;text-align:center">
                    <div style="font-size:11px;color:var(--text-muted)">最优适应度 Best Fitness</div>
                    <div style="font-size:24px;font-weight:700;color:var(--accent-green)">${report.final_best_fitness?.toFixed(4)}</div>
                </div>
                <div style="background:var(--bg-primary);border-radius:8px;padding:12px;text-align:center">
                    <div style="font-size:11px;color:var(--text-muted)">vs 随机 vs Random</div>
                    <div style="font-size:24px;font-weight:700;color:${impColor}">${impSign}${report.improvement_pct}%</div>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0">
                <div style="background:var(--bg-primary);border-radius:8px;padding:10px">
                    <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px">进化均值 Evolved Avg</div>
                    <div style="font-size:16px;font-weight:600;color:var(--accent-green)">${report.final_avg_fitness?.toFixed(6)}</div>
                </div>
                <div style="background:var(--bg-primary);border-radius:8px;padding:10px">
                    <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px">随机基线 Random Baseline</div>
                    <div style="font-size:16px;font-weight:600;color:var(--accent-red)">${report.random_baseline_avg?.toFixed(6)}</div>
                </div>
            </div>

            <div style="background:var(--bg-primary);border-radius:8px;padding:12px;margin:12px 0">
                <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">OKX OnchainOS 工具调用 Tools Used</div>
                <div style="font-size:13px;color:var(--text-primary)">${tools || 'N/A'}</div>
                <div style="display:flex;gap:16px;margin-top:8px;font-size:12px">
                    <span style="color:var(--text-secondary)">执行模式 Mode: <strong style="color:var(--accent-cyan)">${modeLabel}</strong></span>
                </div>
                <div style="display:flex;gap:16px;margin-top:4px;font-size:12px">
                    <span style="color:var(--text-secondary)">行情来源 Data: <strong style="color:var(--accent-green)">${sourceLabel}</strong></span>
                    <span style="color:var(--text-secondary)">总交易数 Trades: <strong>${report.total_trades_executed}</strong></span>
                </div>
            </div>

            ${report.monte_carlo ? `
            <div style="background:var(--bg-primary);border-radius:8px;padding:12px;margin:12px 0;border:1px solid ${report.monte_carlo.statistical_test?.is_significant ? 'var(--accent-green)' : 'var(--accent-red)'}">
                <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px">蒙特卡洛统计验证 Monte Carlo Validation (${report.monte_carlo.n_trials} trials × ${report.monte_carlo.n_regimes} regimes)</div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
                    <div style="text-align:center">
                        <div style="font-size:10px;color:var(--text-muted)">Alpha 超额收益</div>
                        <div style="font-size:18px;font-weight:700;color:${report.monte_carlo.alpha?.annualized_alpha_pct > 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                            ${report.monte_carlo.alpha?.annualized_alpha_pct > 0 ? '+' : ''}${report.monte_carlo.alpha?.annualized_alpha_pct}%
                        </div>
                    </div>
                    <div style="text-align:center">
                        <div style="font-size:10px;color:var(--text-muted)">Sharpe Ratio</div>
                        <div style="font-size:18px;font-weight:700;color:var(--accent-cyan)">${report.monte_carlo.evolved?.avg_sharpe}</div>
                    </div>
                    <div style="text-align:center">
                        <div style="font-size:10px;color:var(--text-muted)">p-value</div>
                        <div style="font-size:18px;font-weight:700;color:${report.monte_carlo.statistical_test?.p_value < 0.05 ? 'var(--accent-green)' : 'var(--accent-yellow)'}">
                            ${report.monte_carlo.statistical_test?.p_value?.toFixed(4)}
                        </div>
                    </div>
                </div>
                <div style="margin-top:8px;padding:6px;border-radius:4px;text-align:center;font-size:12px;font-weight:700;background:${report.monte_carlo.statistical_test?.is_significant ? 'rgba(16,185,129,0.15);color:var(--accent-green)' : 'rgba(245,158,11,0.15);color:var(--accent-yellow)'}">
                    ${report.monte_carlo.statistical_test?.is_significant
                        ? '✓ 统计显著：进化策略显著优于随机 SIGNIFICANT: Evolution generates alpha (p < 0.05)'
                        : '⚠ 未达显著性水平 Not statistically significant yet (p ≥ 0.05)'}
                </div>
                <div style="display:flex;gap:12px;margin-top:6px;font-size:10px;color:var(--text-muted)">
                    <span>Max DD: ${report.monte_carlo.evolved?.avg_max_drawdown_pct}%</span>
                    <span>Info Ratio: ${report.monte_carlo.alpha?.information_ratio}</span>
                    <span>t=${report.monte_carlo.statistical_test?.t_statistic}</span>
                </div>
            </div>
            ` : ''}

            <div style="font-size:11px;color:var(--text-muted);margin:8px 0 4px">Top 5 最优策略 Best Strategies</div>
            <div style="background:var(--bg-primary);border-radius:8px;padding:8px;font-family:'JetBrains Mono',monospace;font-size:11px;max-height:150px;overflow-y:auto">
                ${(report.top5_strategies || []).map((s, i) => `
                    <div style="display:flex;justify-content:space-between;padding:3px 4px;border-bottom:1px solid var(--border)">
                        <span style="color:var(--accent-green)">#${i+1} ${s.id?.slice(0,8)}</span>
                        <span style="color:var(--text-secondary)">${s.strategy_type}/${s.direction}</span>
                        <span style="color:var(--accent-yellow)">${s.leverage?.toFixed(1)}x</span>
                        <span style="font-weight:700;color:${s.fitness_score > 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${s.fitness_score?.toFixed(4)}</span>
                    </div>
                `).join('')}
            </div>

            <div class="btn-row">
                <button class="btn btn-primary" onclick="deployBestStrategy();this.closest('.export-overlay').remove()" style="background:linear-gradient(135deg,var(--accent-yellow),#d97706)">&#9889; 部署最优 Deploy #1</button>
                <button class="btn btn-primary" onclick="exportStrategies()">导出策略 Export</button>
                <button class="btn btn-secondary" onclick="this.closest('.export-overlay').remove()">关闭 Close</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
}

// ─── MCP Stats 集成统计 ───────────────────────────

async function fetchMCPStats() {
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        const mcp = data.mcp || {};
        const el1 = document.getElementById('mcp-calls');
        const el2 = document.getElementById('mcp-tools-used');
        if (el1) el1.textContent = mcp.total_calls || 0;
        if (el2) el2.textContent = mcp.tools_used_count || 0;
    } catch (e) {}
}
// Refresh MCP stats every 10s
setInterval(fetchMCPStats, 10000);
