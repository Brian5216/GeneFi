/**
 * GeneFi Evolution Visualization Engine
 * MiroFish-style force-directed graph with D3.js-like physics
 * Pure SVG implementation - no external dependencies
 */

class EvolutionViz {
    constructor(svgId) {
        this.svg = document.getElementById(svgId);
        this.nodes = new Map();       // id -> node data
        this.links = [];              // parent-child gene links
        this.simulation = null;
        this.width = 0;
        this.height = 0;
        this.tooltip = document.getElementById('tooltip');
        this.animationFrame = null;
        this.particles = [];          // floating particles for ambiance

        // Physics parameters
        this.repulsionForce = 800;
        this.linkDistance = 60;
        this.damping = 0.92;
        this.centerGravity = 0.01;

        // Color scales
        this.fitnessColorScale = (score) => {
            if (score > 0.015) return '#00ff88';  // Elite: bright neon green
            if (score > 0.005) return '#10b981';  // Good: green
            if (score > -0.002) return '#3b82f6'; // Neutral: blue
            if (score > -0.01) return '#ff9900';  // Weak: orange
            return '#ff3333';                      // Eliminate: bright red
        };

        this.typeIcons = {
            'funding_arb': 'F',
            'grid': 'G',
            'momentum': 'M',
            'mean_reversion': 'R',
        };

        this._init();
    }

    _init() {
        this._resize();
        window.addEventListener('resize', () => this._resize());

        // Create SVG groups
        this.defs = this._createSVGElement('defs');
        this.svg.appendChild(this.defs);

        // Glow filters
        this._createGlowFilter('glow-elite', '#10b981');
        this._createGlowFilter('glow-new', '#8b5cf6');
        this._createGlowFilter('glow-death', '#ef4444');

        // Background grid
        this._createGrid();

        this.linkGroup = this._createSVGElement('g', { class: 'links' });
        this.nodeGroup = this._createSVGElement('g', { class: 'nodes' });
        this.particleGroup = this._createSVGElement('g', { class: 'particles', opacity: '0.3' });
        this.svg.appendChild(this.linkGroup);
        this.svg.appendChild(this.nodeGroup);
        this.svg.appendChild(this.particleGroup);

        // Start animation loop
        this._animate();

        // Spawn ambient particles
        this._spawnAmbientParticles();
    }

    _resize() {
        const rect = this.svg.parentElement.getBoundingClientRect();
        this.width = rect.width;
        this.height = rect.height;
        this.svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);
    }

    _createSVGElement(tag, attrs = {}) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [k, v] of Object.entries(attrs)) {
            el.setAttribute(k, v);
        }
        return el;
    }

    _createGlowFilter(id, color) {
        const filter = this._createSVGElement('filter', { id, x: '-50%', y: '-50%', width: '200%', height: '200%' });
        const blur = this._createSVGElement('feGaussianBlur', { stdDeviation: '3', result: 'blur' });
        const flood = this._createSVGElement('feFlood', { 'flood-color': color, 'flood-opacity': '0.6' });
        const comp = this._createSVGElement('feComposite', { in2: 'blur', operator: 'in' });
        const merge = this._createSVGElement('feMerge');
        const mn1 = this._createSVGElement('feMergeNode');
        const mn2 = this._createSVGElement('feMergeNode', { in: 'SourceGraphic' });
        merge.appendChild(mn1);
        merge.appendChild(mn2);
        filter.appendChild(blur);
        filter.appendChild(flood);
        filter.appendChild(comp);
        filter.appendChild(merge);
        this.defs.appendChild(filter);
    }

    _createGrid() {
        const gridGroup = this._createSVGElement('g', { class: 'grid', opacity: '0.05' });
        const spacing = 40;
        for (let x = 0; x < 2000; x += spacing) {
            const line = this._createSVGElement('line', {
                x1: x, y1: 0, x2: x, y2: 2000,
                stroke: '#3b82f6', 'stroke-width': '0.5'
            });
            gridGroup.appendChild(line);
        }
        for (let y = 0; y < 2000; y += spacing) {
            const line = this._createSVGElement('line', {
                x1: 0, y1: y, x2: 2000, y2: y,
                stroke: '#3b82f6', 'stroke-width': '0.5'
            });
            gridGroup.appendChild(line);
        }
        this.svg.appendChild(gridGroup);
    }

    // ─── Population Update ────────────────────────────

    updatePopulation(population) {
        const newIds = new Set(population.map(s => s.id));
        const currentIds = new Set(this.nodes.keys());

        // Remove dead nodes with animation
        for (const id of currentIds) {
            if (!newIds.has(id)) {
                this._removeNode(id);
            }
        }

        // Add or update nodes
        for (const strategy of population) {
            if (this.nodes.has(strategy.id)) {
                this._updateNode(strategy);
            } else {
                this._addNode(strategy);
            }
        }

        // Rebuild links
        this._rebuildLinks(population);
    }

    _addNode(strategy) {
        const genes = strategy.genes || strategy;
        const x = this.width / 2 + (Math.random() - 0.5) * this.width * 0.6;
        const y = this.height / 2 + (Math.random() - 0.5) * this.height * 0.6;

        const node = {
            id: strategy.id,
            x, y, vx: 0, vy: 0,
            generation: strategy.generation,
            parent_id: strategy.parent_id,
            fitness: strategy.fitness_score || 0,
            alive: strategy.alive !== false,
            genes: genes,
            performance: strategy.performance || {},
            virtualBalance: strategy.virtual_balance || 10000,
            balancePnlPct: strategy.balance_pnl_pct || 0,
            radius: this._fitnessToRadius(strategy.fitness_score || 0),
            color: this.fitnessColorScale(strategy.fitness_score || 0),
            age: 0,
            spawning: true,
        };

        this.nodes.set(strategy.id, node);

        // Create SVG elements
        const group = this._createSVGElement('g', {
            class: 'node',
            'data-id': strategy.id,
            opacity: '0',
        });

        // Outer ring (fitness indicator)
        const ring = this._createSVGElement('circle', {
            class: 'node-ring',
            cx: x, cy: y,
            r: node.radius + 4,
            fill: 'none',
            stroke: node.color,
            'stroke-width': '1.5',
            'stroke-dasharray': '3,3',
            opacity: '0.4',
        });

        // Main circle
        const circle = this._createSVGElement('circle', {
            class: 'node-body',
            cx: x, cy: y,
            r: node.radius,
            fill: node.color,
            opacity: '0.8',
            filter: node.fitness > 0.02 ? 'url(#glow-elite)' : '',
        });

        // Strategy type label
        const typeLabel = this.typeIcons[genes.strategy_type || genes?.strategy_type] || '?';
        const text = this._createSVGElement('text', {
            class: 'node-label',
            x: x, y: y + 1,
            'text-anchor': 'middle',
            'dominant-baseline': 'middle',
            'font-size': '10',
            'font-weight': '700',
            fill: '#fff',
            'pointer-events': 'none',
        });
        text.textContent = typeLabel;

        // Direction arrow
        const arrowChar = { long: '↑', short: '↓', neutral: '↔' }[genes.direction || 'neutral'];
        const arrow = this._createSVGElement('text', {
            class: 'node-direction',
            x: x, y: y - node.radius - 8,
            'text-anchor': 'middle',
            'font-size': '12',
            fill: node.color,
            opacity: '0.7',
            'pointer-events': 'none',
        });
        arrow.textContent = arrowChar;

        group.appendChild(ring);
        group.appendChild(circle);
        group.appendChild(text);
        group.appendChild(arrow);
        this.nodeGroup.appendChild(group);

        node.el = group;
        node.circleEl = circle;
        node.ringEl = ring;
        node.textEl = text;
        node.arrowEl = arrow;

        // Event handlers
        group.addEventListener('mouseenter', (e) => this._showTooltip(e, node));
        group.addEventListener('mouseleave', () => this._hideTooltip());

        // Spawn animation
        this._animateSpawn(group, node.radius);
    }

    _updateNode(strategy) {
        const node = this.nodes.get(strategy.id);
        if (!node) return;

        node.fitness = strategy.fitness_score || 0;
        node.alive = strategy.alive !== false;
        node.performance = strategy.performance || {};
        node.virtualBalance = strategy.virtual_balance || node.virtualBalance || 10000;
        node.balancePnlPct = strategy.balance_pnl_pct || 0;
        node.radius = this._fitnessToRadius(node.fitness);
        node.color = this.fitnessColorScale(node.fitness);

        // Update visuals
        if (node.circleEl) {
            node.circleEl.setAttribute('fill', node.color);
            node.circleEl.setAttribute('r', node.radius);
            // Stronger glow for elite, pulsing ring for eliminated
            if (node.fitness > 0.015) {
                node.circleEl.setAttribute('filter', 'url(#glow-elite)');
                node.circleEl.setAttribute('opacity', '0.95');
            } else if (node.fitness < -0.01) {
                node.circleEl.setAttribute('filter', '');
                node.circleEl.setAttribute('opacity', '0.5');
            } else {
                node.circleEl.setAttribute('filter', '');
                node.circleEl.setAttribute('opacity', '0.8');
            }
        }
        if (node.ringEl) {
            node.ringEl.setAttribute('stroke', node.color);
            node.ringEl.setAttribute('r', node.radius + 4);
            // Elite gets visible ring, eliminate gets dashed
            if (node.fitness > 0.015) {
                node.ringEl.setAttribute('opacity', '0.7');
                node.ringEl.setAttribute('stroke-dasharray', '');
                node.ringEl.setAttribute('stroke-width', '2');
            } else if (node.fitness < -0.01) {
                node.ringEl.setAttribute('opacity', '0.6');
                node.ringEl.setAttribute('stroke-dasharray', '2,2');
                node.ringEl.setAttribute('stroke-width', '1');
            } else {
                node.ringEl.setAttribute('opacity', '0.4');
                node.ringEl.setAttribute('stroke-dasharray', '3,3');
                node.ringEl.setAttribute('stroke-width', '1.5');
            }
        }
    }

    _removeNode(id) {
        const node = this.nodes.get(id);
        if (!node || !node.el) return;

        // Death animation
        node.el.style.transition = 'opacity 0.6s';
        node.el.setAttribute('opacity', '0');

        // Emit death particles
        this._emitParticles(node.x, node.y, '#ef4444', 8);

        setTimeout(() => {
            node.el.remove();
            this.nodes.delete(id);
        }, 600);
    }

    _rebuildLinks(population) {
        // Clear existing links
        while (this.linkGroup.firstChild) {
            this.linkGroup.firstChild.remove();
        }
        this.links = [];

        for (const strategy of population) {
            if (!strategy.parent_id) continue;

            // Handle crossover parents (e.g., "abc+def")
            const parentIds = strategy.parent_id.split('+');
            for (const pid of parentIds) {
                if (this.nodes.has(pid)) {
                    const link = { source: pid, target: strategy.id };
                    this.links.push(link);

                    const sourceNode = this.nodes.get(pid);
                    const targetNode = this.nodes.get(strategy.id);
                    if (sourceNode && targetNode) {
                        const line = this._createSVGElement('line', {
                            class: 'gene-link',
                            x1: sourceNode.x, y1: sourceNode.y,
                            x2: targetNode.x, y2: targetNode.y,
                            stroke: '#3b82f6',
                            'stroke-width': '0.8',
                            'stroke-dasharray': '4,4',
                            opacity: '0.2',
                        });
                        link.el = line;
                        this.linkGroup.appendChild(line);
                    }
                }
            }
        }
    }

    // ─── Physics Simulation ───────────────────────────

    _animate() {
        this._step();
        this.animationFrame = requestAnimationFrame(() => this._animate());
    }

    _step() {
        const nodes = Array.from(this.nodes.values());
        if (nodes.length === 0) return;

        // Apply forces
        for (let i = 0; i < nodes.length; i++) {
            const a = nodes[i];

            // Center gravity
            a.vx += (this.width / 2 - a.x) * this.centerGravity;
            a.vy += (this.height / 2 - a.y) * this.centerGravity;

            // Repulsion between nodes
            for (let j = i + 1; j < nodes.length; j++) {
                const b = nodes[j];
                const dx = a.x - b.x;
                const dy = a.y - b.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const minDist = a.radius + b.radius + 20;

                if (dist < minDist * 3) {
                    const force = this.repulsionForce / (dist * dist);
                    const fx = dx / dist * force;
                    const fy = dy / dist * force;
                    a.vx += fx;
                    a.vy += fy;
                    b.vx -= fx;
                    b.vy -= fy;
                }
            }
        }

        // Apply link attraction
        for (const link of this.links) {
            const source = this.nodes.get(link.source);
            const target = this.nodes.get(link.target);
            if (!source || !target) continue;

            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = (dist - this.linkDistance) * 0.005;
            const fx = dx / dist * force;
            const fy = dy / dist * force;

            source.vx += fx;
            source.vy += fy;
            target.vx -= fx;
            target.vy -= fy;
        }

        // Update positions
        for (const node of nodes) {
            node.vx *= this.damping;
            node.vy *= this.damping;
            node.x += node.vx;
            node.y += node.vy;

            // Boundary constraints
            const margin = 30;
            node.x = Math.max(margin, Math.min(this.width - margin, node.x));
            node.y = Math.max(margin, Math.min(this.height - margin, node.y));

            // Update SVG positions
            if (node.circleEl) {
                node.circleEl.setAttribute('cx', node.x);
                node.circleEl.setAttribute('cy', node.y);
            }
            if (node.ringEl) {
                node.ringEl.setAttribute('cx', node.x);
                node.ringEl.setAttribute('cy', node.y);
                // Rotate dashed ring
                const angle = (Date.now() / 50) % 360;
                node.ringEl.setAttribute('transform',
                    `rotate(${angle}, ${node.x}, ${node.y})`);
            }
            if (node.textEl) {
                node.textEl.setAttribute('x', node.x);
                node.textEl.setAttribute('y', node.y + 1);
            }
            if (node.arrowEl) {
                node.arrowEl.setAttribute('x', node.x);
                node.arrowEl.setAttribute('y', node.y - node.radius - 8);
            }

            // Spawn animation
            if (node.spawning) {
                node.age++;
                const opacity = Math.min(1, node.age / 30);
                node.el.setAttribute('opacity', opacity);
                if (node.age > 30) node.spawning = false;
            }
        }

        // Update links
        for (const link of this.links) {
            const source = this.nodes.get(link.source);
            const target = this.nodes.get(link.target);
            if (link.el && source && target) {
                link.el.setAttribute('x1', source.x);
                link.el.setAttribute('y1', source.y);
                link.el.setAttribute('x2', target.x);
                link.el.setAttribute('y2', target.y);
            }
        }

        // Update ambient particles
        this._updateParticles();
    }

    // ─── Particles ────────────────────────────────────

    _emitParticles(x, y, color, count = 5) {
        for (let i = 0; i < count; i++) {
            const angle = (Math.PI * 2 / count) * i;
            const speed = 1 + Math.random() * 2;
            const particle = {
                x, y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: 40 + Math.random() * 20,
                maxLife: 60,
                color,
                radius: 2 + Math.random() * 2,
            };

            const el = this._createSVGElement('circle', {
                cx: x, cy: y, r: particle.radius,
                fill: color, opacity: '0.8',
            });
            this.particleGroup.appendChild(el);
            particle.el = el;
            this.particles.push(particle);
        }
    }

    _spawnAmbientParticles() {
        setInterval(() => {
            if (this.nodes.size > 0) {
                const nodesArr = Array.from(this.nodes.values());
                const randomNode = nodesArr[Math.floor(Math.random() * nodesArr.length)];
                if (randomNode) {
                    this._emitParticles(
                        randomNode.x + (Math.random() - 0.5) * 20,
                        randomNode.y + (Math.random() - 0.5) * 20,
                        randomNode.color + '66',
                        2
                    );
                }
            }
        }, 800);
    }

    _updateParticles() {
        const dead = [];
        for (const p of this.particles) {
            p.x += p.vx;
            p.y += p.vy;
            p.vx *= 0.98;
            p.vy *= 0.98;
            p.life--;

            const opacity = Math.max(0, p.life / p.maxLife);
            if (p.el) {
                p.el.setAttribute('cx', p.x);
                p.el.setAttribute('cy', p.y);
                p.el.setAttribute('opacity', opacity);
                p.el.setAttribute('r', p.radius * opacity);
            }

            if (p.life <= 0) {
                dead.push(p);
            }
        }

        for (const p of dead) {
            if (p.el) p.el.remove();
            const idx = this.particles.indexOf(p);
            if (idx > -1) this.particles.splice(idx, 1);
        }
    }

    // ─── Visual Helpers ───────────────────────────────

    _fitnessToRadius(fitness) {
        const minR = 8;
        const maxR = 22;
        const normalized = Math.max(0, Math.min(1, (fitness + 0.05) / 0.10));
        return minR + normalized * (maxR - minR);
    }

    _animateSpawn(group, targetRadius) {
        group.setAttribute('opacity', '0');
        let frame = 0;
        const animate = () => {
            frame++;
            const progress = Math.min(1, frame / 20);
            const ease = 1 - Math.pow(1 - progress, 3);
            group.setAttribute('opacity', ease);
            if (progress < 1) requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
    }

    // ─── Tooltip ──────────────────────────────────────

    _showTooltip(event, node) {
        const genes = node.genes?.genes || node.genes || {};
        const perf = node.performance || {};
        const fitness = node.fitness || 0;
        const bal = node.virtualBalance || 10000;
        const balPnl = node.balancePnlPct || 0;
        const balColor = balPnl > 0 ? '#10b981' : balPnl < 0 ? '#ef4444' : '#94a3b8';

        // 策略类型中英文 Strategy type bilingual
        const typeBI = { funding_arb: '资金费率套利 Funding Arb', grid: '网格策略 Grid', momentum: '动量策略 Momentum', mean_reversion: '均值回归 Mean Reversion' };
        const dirBI = { long: '做多 Long', short: '做空 Short', neutral: '中性 Neutral' };

        this.tooltip.innerHTML = `
            <div class="tt-header">
                <span class="tt-id">${node.id}</span>
                <span class="tt-gen">第${node.generation}代 Gen ${node.generation}</span>
            </div>
            <div class="tt-row" style="background:rgba(0,0,0,0.2);border-radius:4px;padding:4px;margin:4px 0">
                <span class="tt-label" style="font-weight:700">余额 Balance</span>
                <span class="tt-value" style="color:${balColor};font-size:14px;font-weight:700">$${Math.round(bal).toLocaleString()} <span style="font-size:10px">(${balPnl > 0 ? '+' : ''}${balPnl.toFixed(1)}%)</span></span>
            </div>
            <div class="tt-row"><span class="tt-label">类型 Type</span><span class="tt-value">${typeBI[genes.strategy_type] || genes.strategy_type || '--'}</span></div>
            <div class="tt-row"><span class="tt-label">方向 Direction</span><span class="tt-value">${dirBI[genes.direction] || genes.direction || '--'}</span></div>
            <div class="tt-row"><span class="tt-label">杠杆 Leverage</span><span class="tt-value">${(genes.leverage || 0).toFixed(1)}x</span></div>
            <div class="tt-row"><span class="tt-label">对冲 Hedge</span><span class="tt-value">${((genes.hedge_ratio || 0) * 100).toFixed(0)}%</span></div>
            <div class="tt-row"><span class="tt-label">链 Chain</span><span class="tt-value">${genes.chain || '--'}</span></div>
            <div style="margin:6px 0;border-top:1px solid #2a3a4e"></div>
            <div class="tt-row"><span class="tt-label">适应度 Fitness</span><span class="tt-value" style="color:${this.fitnessColorScale(fitness)}">${fitness.toFixed(4)}</span></div>
            <div class="tt-row"><span class="tt-label">本代盈亏 PnL</span><span class="tt-value">${((perf.pnl_pct || 0) * 100).toFixed(2)}%</span></div>
            <div class="tt-row"><span class="tt-label">资金费收益 Funding</span><span class="tt-value">${((perf.funding_yield || 0) * 100).toFixed(3)}%</span></div>
            <div class="tt-row"><span class="tt-label">最大回撤 MaxDD</span><span class="tt-value" style="color:#ef4444">${((perf.max_drawdown || 0) * 100).toFixed(2)}%</span></div>
            <div class="tt-row"><span class="tt-label">胜率 Win Rate</span><span class="tt-value">${((perf.win_rate || 0) * 100).toFixed(0)}%</span></div>
            ${node.parent_id ? `<div class="tt-row"><span class="tt-label">父代 Parent</span><span class="tt-value">${node.parent_id}</span></div>` : ''}
        `;

        const rect = this.svg.getBoundingClientRect();
        let left = event.clientX - rect.left + 15;
        let top = event.clientY - rect.top - 10;

        // Keep tooltip in bounds
        if (left + 220 > this.width) left = left - 240;
        if (top + 200 > this.height) top = top - 200;

        this.tooltip.style.left = left + 'px';
        this.tooltip.style.top = top + 'px';
        this.tooltip.classList.add('visible');
    }

    _hideTooltip() {
        this.tooltip.classList.remove('visible');
    }

    // ─── Highlight Effects ────────────────────────────

    highlightEliminated(ids) {
        for (const id of ids) {
            const node = this.nodes.get(id);
            if (node) {
                this._emitParticles(node.x, node.y, '#ef4444', 10);
            }
        }
    }

    highlightElites(ids) {
        for (const id of ids) {
            const node = this.nodes.get(id);
            if (node) {
                this._emitParticles(node.x, node.y, '#10b981', 6);
            }
        }
    }

    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    }
}
