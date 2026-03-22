"""GeneFi Evolution Engine - Orchestrates the genetic evolution cycle."""
from __future__ import annotations
import time
import random
import json
import os
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, field

from dtes.core.strategy import StrategyGene
from dtes.core.fitness import calculate_fitness, rank_population
from config import Config


@dataclass
class GenerationSnapshot:
    """Snapshot of a single generation for audit trail."""
    generation: int
    timestamp: float
    population: List[dict]
    avg_fitness: float
    best_fitness: float
    worst_fitness: float
    eliminated_count: int
    mutated_count: int
    crossover_count: int
    market_regime: str = "normal"

    def to_dict(self) -> dict:
        return {
            "generation": self.generation,
            "timestamp": self.timestamp,
            "population_size": len(self.population),
            "avg_fitness": self.avg_fitness,
            "best_fitness": self.best_fitness,
            "worst_fitness": self.worst_fitness,
            "eliminated_count": self.eliminated_count,
            "mutated_count": self.mutated_count,
            "crossover_count": self.crossover_count,
            "market_regime": self.market_regime,
            "population": self.population,
        }


class EvolutionEngine:
    """Core evolution loop: Generate → Execute → Judge → Evolve."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.population: List[StrategyGene] = []
        self.generation: int = 0
        self.history: List[GenerationSnapshot] = []
        self.is_running: bool = False
        self._event_callbacks: List[Callable] = []

    def on_event(self, callback: Callable):
        """Register a callback for evolution events."""
        self._event_callbacks.append(callback)

    async def _emit(self, event_type: str, data: dict):
        for cb in self._event_callbacks:
            try:
                result = cb(event_type, data)
                if hasattr(result, "__await__"):
                    await result
            except Exception:
                pass

    def initialize_population(self, size: Optional[int] = None) -> list[StrategyGene]:
        """Generate initial random population (Genesis)."""
        size = size or self.config.POPULATION_SIZE
        self.population = [StrategyGene.random(generation=0) for _ in range(size)]
        self.generation = 0
        return self.population

    async def run_generation(
        self,
        predictor_fn: Optional[Callable] = None,
        executor_fn: Optional[Callable] = None,
        judge_fn: Optional[Callable] = None,
        market_data: Optional[dict] = None,
    ) -> GenerationSnapshot:
        """Execute one full evolution generation cycle."""

        await self._emit("generation_start", {
            "generation": self.generation,
            "population_size": len(self.population),
        })

        # Phase 1: Predict / Generate new candidates if needed
        if predictor_fn:
            new_candidates = await predictor_fn(self.population, market_data)
            if new_candidates:
                self.population.extend(new_candidates)

        # Phase 2: Execute strategies and collect performance
        if executor_fn:
            self.population = await executor_fn(self.population, market_data)

        # Phase 3: Judge - Score fitness
        if judge_fn:
            self.population = await judge_fn(self.population, market_data)
        else:
            # Default scoring
            for s in self.population:
                result = calculate_fitness(
                    s.pnl_pct, s.funding_yield, s.max_drawdown,
                    self.config.PNL_WEIGHT, self.config.FUNDING_WEIGHT, self.config.DRAWDOWN_WEIGHT,
                )
                s.fitness_score = result.score

        # Phase 4: Selection & Evolution
        ranked = rank_population(self.population, self.config.SELECTION_PRESSURE)

        elites = []
        survivors = []
        eliminated = []

        for strategy, result in ranked:
            if result.recommendation == "elite":
                strategy.alive = True
                elites.append(strategy)
            elif result.recommendation == "survive":
                strategy.alive = True
                survivors.append(strategy)
            else:
                strategy.alive = False
                eliminated.append(strategy)

        await self._emit("selection_complete", {
            "generation": self.generation,
            "elites": len(elites),
            "survivors": len(survivors),
            "eliminated": len(eliminated),
            "eliminated_ids": [s.id for s in eliminated],
        })

        # ── Snapshot BEFORE reproduction (only scored strategies) ──
        scored_pop = elites + survivors + eliminated
        fitness_scores = [s.fitness_score for s in scored_pop]

        # Phase 5: Reproduction - Mutation + Crossover
        new_generation = list(elites) + list(survivors)
        mutated_count = 0
        crossover_count = 0

        # Fill eliminated slots with offspring
        while len(new_generation) < self.config.POPULATION_SIZE:
            if elites and random.random() < 0.6:
                # Crossover between two elites
                if len(elites) >= 2:
                    p1, p2 = random.sample(elites, 2)
                    child = StrategyGene.crossover(p1, p2)
                    child.generation = self.generation + 1
                    child = child.mutate(self.config.MUTATION_RATE * 0.5)
                    new_generation.append(child)
                    crossover_count += 1
                else:
                    child = elites[0].mutate(self.config.MUTATION_RATE)
                    new_generation.append(child)
                    mutated_count += 1
            elif elites or survivors:
                parent = random.choice(elites + survivors)
                child = parent.mutate(self.config.MUTATION_RATE)
                new_generation.append(child)
                mutated_count += 1
            else:
                new_generation.append(StrategyGene.random(generation=self.generation + 1))
                mutated_count += 1

        self.population = new_generation[:self.config.POPULATION_SIZE]

        # Create snapshot using PRE-reproduction data (only scored individuals)
        snapshot = GenerationSnapshot(
            generation=self.generation,
            timestamp=time.time(),
            population=[s.to_dict() for s in scored_pop],
            avg_fitness=round(sum(fitness_scores) / len(fitness_scores), 6) if fitness_scores else 0,
            best_fitness=round(max(fitness_scores), 6) if fitness_scores else 0,
            worst_fitness=round(min(fitness_scores), 6) if fitness_scores else 0,
            eliminated_count=len(eliminated),
            mutated_count=mutated_count,
            crossover_count=crossover_count,
            market_regime=market_data.get("regime", "normal") if market_data else "normal",
        )
        self.history.append(snapshot)

        await self._emit("generation_complete", snapshot.to_dict())

        # Save audit log
        self._save_audit_log(snapshot)

        self.generation += 1
        return snapshot

    def _save_audit_log(self, snapshot: GenerationSnapshot):
        """Save generation snapshot to JSON audit log."""
        os.makedirs(self.config.LOG_DIR, exist_ok=True)
        log_file = os.path.join(
            self.config.LOG_DIR,
            f"gen_{snapshot.generation:04d}_{int(snapshot.timestamp)}.json",
        )
        with open(log_file, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    def get_population_stats(self) -> dict:
        """Get current population statistics."""
        if not self.population:
            return {"generation": self.generation, "population_size": 0}

        # Only include scored individuals (exclude newborns with fitness=0)
        scored = [s for s in self.population if s.fitness_score != 0 or s.trades_count > 0]
        if not scored:
            scored = self.population  # Fallback: all have fitness=0 (gen 0)
        fitness_scores = [s.fitness_score for s in scored]
        alive_count = sum(1 for s in self.population if s.alive)

        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "scored_count": len(scored),
            "alive_count": alive_count,
            "avg_fitness": round(sum(fitness_scores) / len(fitness_scores), 4),
            "best_fitness": round(max(fitness_scores), 4),
            "worst_fitness": round(min(fitness_scores), 4),
            "strategy_types": {
                t: sum(1 for s in self.population if s.strategy_type == t)
                for t in set(s.strategy_type for s in self.population)
            },
            "direction_distribution": {
                d: sum(1 for s in self.population if s.direction == d)
                for d in set(s.direction for s in self.population)
            },
            "history_length": len(self.history),
        }
