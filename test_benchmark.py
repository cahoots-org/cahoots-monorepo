"""Test script to run a quick benchmark demonstration."""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from benchmarks.run_benchmarks import setup_components, cleanup_components, run_quick_benchmark
from benchmarks.comparison_analyzer import ComparisonAnalyzer


async def main():
    """Run a quick benchmark test."""
    print("Starting benchmark demonstration...")

    try:
        # Setup components
        processor, redis_client = await setup_components()

        # Run quick benchmark (just 3 tasks)
        suite = await run_quick_benchmark(processor, task_count=3)

        # Print basic results
        print("\n" + "="*60)
        print("QUICK BENCHMARK RESULTS")
        print("="*60)

        stats = suite.get_overall_stats()
        print(f"Total Runs: {stats['total_runs']}")
        print(f"Success Rate: {stats['success_rate']:.1%}")
        print(f"Average Time: {stats['avg_time']:.2f}s")
        print(f"Average LLM Calls: {stats['avg_llm_calls']:.1f}")
        print(f"Cache Hit Rate: {stats['overall_cache_hit_rate']:.1%}")

        # Run comparison analysis
        print("\n" + "="*60)
        print("OPTIMIZATION ANALYSIS")
        print("="*60)

        analyzer = ComparisonAnalyzer(suite)
        analyzer.print_comparison_report()

        # Create results directory and save
        os.makedirs("benchmarks/results", exist_ok=True)
        suite.export_results("benchmarks/results/demo_benchmark.json")
        analyzer.export_comparison_report("benchmarks/results/demo_comparison.json")

        print(f"\n✓ Results saved to benchmarks/results/")
        print("✓ Benchmark demonstration completed successfully!")

        return True

    except Exception as e:
        print(f"Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        await cleanup_components(redis_client)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)