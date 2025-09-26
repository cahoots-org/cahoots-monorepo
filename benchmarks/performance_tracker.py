"""Performance tracking utilities for benchmarking."""

import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path

from app.models import Task, TaskStatus, TaskRequest
from app.processor import TaskProcessor


@dataclass
class BenchmarkResult:
    """Single benchmark run result."""
    task_description: str
    task_type: str  # simple, medium, complex

    # Performance metrics
    total_time: float
    llm_calls: int
    cache_hits: int
    cache_misses: int

    # Task metrics
    tasks_created: int
    atomic_tasks: int
    max_depth: int
    total_story_points: Optional[int]

    # Quality metrics
    completion_percentage: float
    success: bool
    error_message: Optional[str] = None

    # Detailed timing
    analysis_time: float = 0.0
    decomposition_time: float = 0.0
    processing_time: float = 0.0

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results with analysis."""
    results: List[BenchmarkResult] = field(default_factory=list)

    def add_result(self, result: BenchmarkResult):
        """Add a benchmark result."""
        self.results.append(result)

    def get_stats_by_type(self, task_type: str) -> Dict[str, Any]:
        """Get aggregated stats for a specific task type."""
        filtered = [r for r in self.results if r.task_type == task_type and r.success]

        if not filtered:
            return {"count": 0}

        return {
            "count": len(filtered),
            "avg_time": sum(r.total_time for r in filtered) / len(filtered),
            "avg_llm_calls": sum(r.llm_calls for r in filtered) / len(filtered),
            "avg_tasks_created": sum(r.tasks_created for r in filtered) / len(filtered),
            "cache_hit_rate": sum(r.cache_hits for r in filtered) / max(1, sum(r.cache_hits + r.cache_misses for r in filtered)),
            "success_rate": len(filtered) / len([r for r in self.results if r.task_type == task_type]),
            "min_time": min(r.total_time for r in filtered),
            "max_time": max(r.total_time for r in filtered),
        }

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall benchmark statistics."""
        successful = [r for r in self.results if r.success]

        if not successful:
            return {"total_runs": len(self.results), "success_rate": 0.0}

        total_cache_requests = sum(r.cache_hits + r.cache_misses for r in successful)

        return {
            "total_runs": len(self.results),
            "successful_runs": len(successful),
            "success_rate": len(successful) / len(self.results),
            "avg_time": sum(r.total_time for r in successful) / len(successful),
            "avg_llm_calls": sum(r.llm_calls for r in successful) / len(successful),
            "overall_cache_hit_rate": sum(r.cache_hits for r in successful) / max(1, total_cache_requests),
            "avg_tasks_per_run": sum(r.tasks_created for r in successful) / len(successful),
            "llm_efficiency": sum(r.cache_hits for r in successful) / max(1, sum(r.llm_calls + r.cache_hits for r in successful)),
        }

    def export_results(self, filepath: str):
        """Export results to JSON file."""
        data = {
            "metadata": {
                "benchmark_time": datetime.now(timezone.utc).isoformat(),
                "total_runs": len(self.results),
                "benchmark_version": "1.0.0"
            },
            "overall_stats": self.get_overall_stats(),
            "stats_by_type": {
                "simple": self.get_stats_by_type("simple"),
                "medium": self.get_stats_by_type("medium"),
                "complex": self.get_stats_by_type("complex"),
            },
            "detailed_results": [
                {
                    "task_description": r.task_description,
                    "task_type": r.task_type,
                    "total_time": r.total_time,
                    "llm_calls": r.llm_calls,
                    "cache_hits": r.cache_hits,
                    "cache_misses": r.cache_misses,
                    "tasks_created": r.tasks_created,
                    "atomic_tasks": r.atomic_tasks,
                    "max_depth": r.max_depth,
                    "success": r.success,
                    "error_message": r.error_message,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


class PerformanceTracker:
    """Tracks performance metrics during task processing."""

    def __init__(self, processor: TaskProcessor):
        self.processor = processor
        self.current_run: Optional[BenchmarkResult] = None

    async def benchmark_task(
        self,
        description: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
        max_depth: int = 5,
        user_id: str = "benchmark-user"
    ) -> BenchmarkResult:
        """Benchmark a single task processing."""

        # Reset processor stats
        await self.processor.reset_stats()

        # Start timing
        start_time = time.time()

        result = BenchmarkResult(
            task_description=description,
            task_type=task_type,
            total_time=0.0,
            llm_calls=0,
            cache_hits=0,
            cache_misses=0,
            tasks_created=0,
            atomic_tasks=0,
            max_depth=0,
            total_story_points=None,
            completion_percentage=0.0,
            success=False
        )

        try:
            # Process the task
            tree = await self.processor.process_task_complete(
                description=description,
                context=context,
                user_id=user_id,
                max_depth=max_depth
            )

            # Calculate timing
            end_time = time.time()
            result.total_time = end_time - start_time

            # Get processor stats
            stats = await self.processor.get_processing_stats()

            # Update result with metrics
            result.llm_calls = stats.get("tasks_processed", 0) - stats.get("cache_hits", 0)
            result.cache_hits = stats.get("cache_hits", 0)
            result.cache_misses = result.llm_calls  # LLM calls that weren't cache hits
            result.tasks_created = len(tree.tasks)
            result.atomic_tasks = stats.get("atomic_tasks", 0)
            result.max_depth = max(tree.depth_map.keys()) if tree.depth_map else 0
            result.total_story_points = sum(t.story_points or 0 for t in tree.tasks.values()) or None
            result.completion_percentage = tree.calculate_completion_percentage()
            result.success = True

        except Exception as e:
            end_time = time.time()
            result.total_time = end_time - start_time
            result.error_message = str(e)
            result.success = False

        return result


class BenchmarkRunner:
    """Runs comprehensive benchmarks."""

    def __init__(self, processor: TaskProcessor):
        self.tracker = PerformanceTracker(processor)
        self.suite = BenchmarkSuite()

    async def run_single_benchmark(self, task_config: Dict[str, Any]) -> BenchmarkResult:
        """Run a single benchmark."""
        result = await self.tracker.benchmark_task(
            description=task_config["description"],
            task_type=task_config["type"],
            context=task_config.get("context"),
            max_depth=task_config.get("max_depth", 5)
        )

        self.suite.add_result(result)
        return result

    async def run_benchmark_suite(self, task_configs: List[Dict[str, Any]], runs_per_task: int = 3) -> BenchmarkSuite:
        """Run complete benchmark suite."""
        total_tasks = len(task_configs) * runs_per_task
        current_task = 0

        print(f"Starting benchmark suite: {total_tasks} total runs")

        for config in task_configs:
            print(f"\nBenchmarking: {config['description']} ({config['type']})")

            for run in range(runs_per_task):
                current_task += 1
                print(f"  Run {run + 1}/{runs_per_task} (Task {current_task}/{total_tasks})")

                result = await self.run_single_benchmark(config)

                if result.success:
                    print(f"    ✓ {result.total_time:.2f}s, {result.llm_calls} LLM calls, {result.tasks_created} tasks")
                else:
                    print(f"    ✗ Failed: {result.error_message}")

                # Small delay between runs to avoid overwhelming the system
                await asyncio.sleep(0.1)

        print(f"\nBenchmark suite completed!")
        return self.suite

    def print_summary(self):
        """Print benchmark summary."""
        stats = self.suite.get_overall_stats()

        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)

        print(f"Total Runs: {stats['total_runs']}")
        print(f"Success Rate: {stats['success_rate']:.1%}")
        print(f"Average Time: {stats['avg_time']:.2f}s")
        print(f"Average LLM Calls: {stats['avg_llm_calls']:.1f}")
        print(f"Cache Hit Rate: {stats['overall_cache_hit_rate']:.1%}")
        print(f"LLM Efficiency: {stats['llm_efficiency']:.1%}")

        print("\nBy Task Type:")
        for task_type in ["simple", "medium", "complex"]:
            type_stats = self.suite.get_stats_by_type(task_type)
            if type_stats["count"] > 0:
                print(f"\n{task_type.upper()}:")
                print(f"  Runs: {type_stats['count']}")
                print(f"  Avg Time: {type_stats['avg_time']:.2f}s ({type_stats['min_time']:.2f}-{type_stats['max_time']:.2f}s)")
                print(f"  Avg LLM Calls: {type_stats['avg_llm_calls']:.1f}")
                print(f"  Cache Hit Rate: {type_stats['cache_hit_rate']:.1%}")
                print(f"  Success Rate: {type_stats['success_rate']:.1%}")


# Predefined benchmark task configurations
BENCHMARK_TASKS = [
    # Simple tasks (should be atomic)
    {
        "description": "Create a hello world function in Python",
        "type": "simple",
        "max_depth": 3
    },
    {
        "description": "Write a function to calculate factorial",
        "type": "simple",
        "max_depth": 3
    },
    {
        "description": "Implement a basic calculator function",
        "type": "simple",
        "max_depth": 3
    },

    # Medium tasks (1-2 levels of decomposition)
    {
        "description": "Create a user authentication system with JWT",
        "type": "medium",
        "max_depth": 4,
        "context": {
            "tech_stack": {
                "backend_language": "Python",
                "framework": "FastAPI",
                "database": "PostgreSQL"
            }
        }
    },
    {
        "description": "Build a REST API for a todo application",
        "type": "medium",
        "max_depth": 4,
        "context": {
            "tech_stack": {
                "backend_language": "Python",
                "framework": "FastAPI",
                "database": "SQLite"
            }
        }
    },
    {
        "description": "Implement a file upload service with validation",
        "type": "medium",
        "max_depth": 4
    },

    # Complex tasks (3+ levels of decomposition)
    {
        "description": "Build a complete e-commerce platform with user management, product catalog, and payment processing",
        "type": "complex",
        "max_depth": 5,
        "context": {
            "tech_stack": {
                "backend_language": "Python",
                "frontend_framework": "React",
                "database": "PostgreSQL",
                "payment_provider": "Stripe"
            }
        }
    },
    {
        "description": "Create a social media application with posts, comments, likes, and real-time notifications",
        "type": "complex",
        "max_depth": 5,
        "context": {
            "tech_stack": {
                "backend_language": "Python",
                "frontend_framework": "React",
                "database": "PostgreSQL",
                "websockets": True
            }
        }
    },
    {
        "description": "Develop a project management system with teams, tasks, time tracking, and reporting",
        "type": "complex",
        "max_depth": 5,
        "context": {
            "tech_stack": {
                "backend_language": "Python",
                "frontend_framework": "Vue.js",
                "database": "PostgreSQL"
            }
        }
    }
]