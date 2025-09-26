"""Main script to run performance benchmarks."""

import asyncio
import argparse
import os
from datetime import datetime
from pathlib import Path

from app.storage import RedisClient, TaskStorage
from app.analyzer import UnifiedAnalyzer, MockLLMClient
from app.cache import CacheManager
from app.processor import TaskProcessor
from app.processor.processing_rules import ProcessingConfig

from .performance_tracker import BenchmarkRunner, BENCHMARK_TASKS
from .comparison_analyzer import ComparisonAnalyzer, HistoricalComparison


async def setup_components():
    """Set up all required components for benchmarking."""
    print("Setting up benchmark environment...")

    # Use mock LLM client for consistent, fast benchmarks
    llm_client = MockLLMClient()
    analyzer = UnifiedAnalyzer(llm_client)

    # Use in-memory storage for benchmarks (faster, isolated)
    redis_client = RedisClient(host="localhost", port=6379, db=15)  # Use separate DB
    await redis_client.connect()

    # Clear benchmark database
    await redis_client.redis.flushdb()

    storage = TaskStorage(redis_client)

    # Set up cache with aggressive caching for benchmarks
    cache_manager = CacheManager(
        redis_client,
        use_semantic_cache=True,
        cache_ttl=3600
    )

    # Configure processor for optimal performance
    config = ProcessingConfig(
        max_depth=5,
        complexity_threshold=0.45,
        batch_sibling_threshold=3,
        use_template_cache=True,
        use_semantic_cache=True
    )

    processor = TaskProcessor(storage, analyzer, cache_manager, config)

    print("✓ Components initialized")
    return processor, redis_client


async def cleanup_components(redis_client: RedisClient):
    """Clean up components after benchmarking."""
    await redis_client.close()
    print("✓ Cleanup completed")


async def run_quick_benchmark(processor: TaskProcessor, task_count: int = 3):
    """Run a quick benchmark with limited tasks."""
    print(f"\nRunning quick benchmark ({task_count} tasks)...")

    # Select a subset of tasks for quick testing
    quick_tasks = BENCHMARK_TASKS[:task_count]

    runner = BenchmarkRunner(processor)
    suite = await runner.run_benchmark_suite(quick_tasks, runs_per_task=1)

    return suite


async def run_full_benchmark(processor: TaskProcessor, runs_per_task: int = 3):
    """Run full benchmark suite."""
    print(f"\nRunning full benchmark (all tasks, {runs_per_task} runs each)...")

    runner = BenchmarkRunner(processor)
    suite = await runner.run_benchmark_suite(BENCHMARK_TASKS, runs_per_task=runs_per_task)

    return suite


async def run_cache_warmup_benchmark(processor: TaskProcessor):
    """Run benchmark to test cache effectiveness."""
    print("\nRunning cache warmup benchmark...")

    # First run - cold cache
    print("Phase 1: Cold cache")
    runner1 = BenchmarkRunner(processor)
    cold_suite = await runner1.run_benchmark_suite(BENCHMARK_TASKS[:3], runs_per_task=1)

    # Second run - warm cache
    print("Phase 2: Warm cache")
    runner2 = BenchmarkRunner(processor)
    warm_suite = await runner2.run_benchmark_suite(BENCHMARK_TASKS[:3], runs_per_task=2)

    return cold_suite, warm_suite


def save_results(suite, output_dir: str, filename_prefix: str):
    """Save benchmark results."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = Path(output_dir) / f"{filename_prefix}_{timestamp}.json"

    suite.export_results(str(filepath))
    print(f"✓ Results saved to: {filepath}")
    return str(filepath)


async def main():
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(description="Run Cahoots performance benchmarks")
    parser.add_argument("--mode", choices=["quick", "full", "cache"], default="quick",
                       help="Benchmark mode (default: quick)")
    parser.add_argument("--runs", type=int, default=3,
                       help="Number of runs per task (default: 3)")
    parser.add_argument("--output", default="benchmarks/results",
                       help="Output directory for results (default: benchmarks/results)")
    parser.add_argument("--compare", action="store_true",
                       help="Generate comparison analysis")
    parser.add_argument("--historical",
                       help="Path to historical results for comparison")

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    try:
        # Setup
        processor, redis_client = await setup_components()

        # Run benchmark based on mode
        if args.mode == "quick":
            suite = await run_quick_benchmark(processor, task_count=6)
            results_file = save_results(suite, args.output, "quick_benchmark")

        elif args.mode == "full":
            suite = await run_full_benchmark(processor, runs_per_task=args.runs)
            results_file = save_results(suite, args.output, "full_benchmark")

        elif args.mode == "cache":
            cold_suite, warm_suite = await run_cache_warmup_benchmark(processor)
            cold_file = save_results(cold_suite, args.output, "cold_cache_benchmark")
            warm_file = save_results(warm_suite, args.output, "warm_cache_benchmark")
            suite = warm_suite  # Use warm cache results for analysis
            results_file = warm_file

        # Print summary
        runner = BenchmarkRunner(processor)
        runner.suite = suite
        runner.print_summary()

        # Generate comparison analysis if requested
        if args.compare:
            print("\nGenerating comparison analysis...")
            analyzer = ComparisonAnalyzer(suite)
            analyzer.print_comparison_report()

            # Save comparison report
            comparison_file = Path(args.output) / f"comparison_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            analyzer.export_comparison_report(str(comparison_file))
            print(f"✓ Comparison analysis saved to: {comparison_file}")

        # Historical comparison if provided
        if args.historical:
            print("\nGenerating historical comparison...")
            historical = HistoricalComparison(suite)
            comparison = historical.compare_with_historical(args.historical)
            if comparison:
                print("Historical Comparison Results:")
                print(f"  Time improvement: {comparison['time_delta']['improvement']:.1%}")
                print(f"  LLM efficiency improvement: {comparison['llm_efficiency_delta']['improvement']:.1%}")
                print(f"  Cache hit rate change: {comparison['cache_delta']['improvement']:+.1%}")
            else:
                print("Could not load historical data for comparison")

        return 0

    except Exception as e:
        print(f"Benchmark failed: {e}")
        return 1

    finally:
        # Cleanup
        await cleanup_components(redis_client)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)