"""Stress testing for concurrent task processing."""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import random

from app.processor import TaskProcessor
from .performance_tracker import PerformanceTracker, BENCHMARK_TASKS


@dataclass
class StressTestResult:
    """Results from a stress test run."""
    concurrent_tasks: int
    total_time: float
    successful_tasks: int
    failed_tasks: int
    avg_task_time: float
    min_task_time: float
    max_task_time: float
    tasks_per_second: float
    error_rate: float


class StressTestRunner:
    """Runs stress tests with concurrent task processing."""

    def __init__(self, processor: TaskProcessor):
        self.processor = processor
        self.tracker = PerformanceTracker(processor)

    async def run_concurrent_tasks(self, task_configs: List[Dict[str, Any]], concurrent_count: int) -> StressTestResult:
        """Run multiple tasks concurrently."""
        print(f"Running {concurrent_count} concurrent tasks...")

        # Prepare tasks
        tasks_to_run = []
        for i in range(concurrent_count):
            # Cycle through available task configs
            config = task_configs[i % len(task_configs)]
            tasks_to_run.append(config)

        # Track timing and results
        start_time = time.time()
        task_times = []
        successful = 0
        failed = 0

        # Run tasks concurrently
        async def run_single_task(config):
            task_start = time.time()
            try:
                result = await self.tracker.benchmark_task(
                    description=config["description"],
                    task_type=config["type"],
                    context=config.get("context"),
                    max_depth=config.get("max_depth", 5),
                    user_id=f"stress-user-{random.randint(1000, 9999)}"
                )
                task_end = time.time()
                return task_end - task_start, result.success
            except Exception as e:
                task_end = time.time()
                print(f"Task failed: {e}")
                return task_end - task_start, False

        # Execute all tasks concurrently
        results = await asyncio.gather(*[run_single_task(config) for config in tasks_to_run])

        total_time = time.time() - start_time

        # Process results
        for task_time, success in results:
            task_times.append(task_time)
            if success:
                successful += 1
            else:
                failed += 1

        # Calculate metrics
        return StressTestResult(
            concurrent_tasks=concurrent_count,
            total_time=total_time,
            successful_tasks=successful,
            failed_tasks=failed,
            avg_task_time=statistics.mean(task_times) if task_times else 0,
            min_task_time=min(task_times) if task_times else 0,
            max_task_time=max(task_times) if task_times else 0,
            tasks_per_second=successful / total_time if total_time > 0 else 0,
            error_rate=failed / concurrent_count if concurrent_count > 0 else 0
        )

    async def run_load_test(self, max_concurrent: int = 50, step_size: int = 10) -> List[StressTestResult]:
        """Run increasing load test."""
        print(f"Running load test: 1 to {max_concurrent} concurrent tasks")

        # Use simpler tasks for stress testing
        simple_tasks = [task for task in BENCHMARK_TASKS if task["type"] == "simple"]

        results = []

        for concurrent in range(step_size, max_concurrent + 1, step_size):
            print(f"\nTesting {concurrent} concurrent tasks...")

            # Reset processor stats before each run
            await self.processor.reset_stats()

            result = await self.run_concurrent_tasks(simple_tasks, concurrent)
            results.append(result)

            print(f"  ✓ {result.successful_tasks}/{result.concurrent_tasks} successful")
            print(f"    {result.tasks_per_second:.1f} tasks/sec, {result.error_rate:.1%} error rate")

            # Brief pause between tests
            await asyncio.sleep(1)

        return results

    async def run_sustained_load_test(self, concurrent_tasks: int = 20, duration_seconds: int = 60) -> Dict[str, Any]:
        """Run sustained load for a specific duration."""
        print(f"Running sustained load test: {concurrent_tasks} concurrent tasks for {duration_seconds}s")

        simple_tasks = [task for task in BENCHMARK_TASKS if task["type"] == "simple"]
        start_time = time.time()
        end_time = start_time + duration_seconds

        total_completed = 0
        total_failed = 0
        completion_times = []

        while time.time() < end_time:
            batch_start = time.time()

            # Run a batch of concurrent tasks
            result = await self.run_concurrent_tasks(simple_tasks, concurrent_tasks)

            batch_time = time.time() - batch_start
            completion_times.append(batch_time)

            total_completed += result.successful_tasks
            total_failed += result.failed_tasks

            print(f"  Batch: {result.successful_tasks}/{result.concurrent_tasks} successful in {batch_time:.2f}s")

            # Small delay between batches
            await asyncio.sleep(0.5)

        total_time = time.time() - start_time

        return {
            "duration": total_time,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "avg_throughput": total_completed / total_time,
            "avg_batch_time": statistics.mean(completion_times),
            "success_rate": total_completed / (total_completed + total_failed) if (total_completed + total_failed) > 0 else 0
        }

    def print_load_test_results(self, results: List[StressTestResult]):
        """Print load test results."""
        print("\n" + "="*80)
        print("LOAD TEST RESULTS")
        print("="*80)

        print(f"{'Concurrent':<12} {'Success Rate':<12} {'Tasks/Sec':<12} {'Avg Time':<12} {'Error Rate'}")
        print("-" * 60)

        for result in results:
            print(f"{result.concurrent_tasks:<12} "
                  f"{result.successful_tasks/result.concurrent_tasks:<12.1%} "
                  f"{result.tasks_per_second:<12.1f} "
                  f"{result.avg_task_time:<12.2f} "
                  f"{result.error_rate:<12.1%}")

        # Find optimal performance point
        optimal = max(results, key=lambda r: r.tasks_per_second * (1 - r.error_rate))
        print(f"\nOptimal Performance: {optimal.concurrent_tasks} concurrent tasks")
        print(f"  Throughput: {optimal.tasks_per_second:.1f} tasks/sec")
        print(f"  Success Rate: {optimal.successful_tasks/optimal.concurrent_tasks:.1%}")


async def run_stress_tests(processor: TaskProcessor):
    """Run all stress tests."""
    runner = StressTestRunner(processor)

    # 1. Load test with increasing concurrency
    print("1. Load Test with Increasing Concurrency")
    load_results = await runner.run_load_test(max_concurrent=30, step_size=5)
    runner.print_load_test_results(load_results)

    # 2. Sustained load test
    print("\n2. Sustained Load Test")
    sustained_results = await runner.run_sustained_load_test(concurrent_tasks=15, duration_seconds=30)

    print(f"\nSustained Load Results ({sustained_results['duration']:.0f}s):")
    print(f"  Total Completed: {sustained_results['total_completed']}")
    print(f"  Total Failed: {sustained_results['total_failed']}")
    print(f"  Average Throughput: {sustained_results['avg_throughput']:.1f} tasks/sec")
    print(f"  Success Rate: {sustained_results['success_rate']:.1%}")

    return {
        "load_test": load_results,
        "sustained_test": sustained_results
    }