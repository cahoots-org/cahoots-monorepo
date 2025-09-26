"""Analyzes performance improvements compared to microservices baseline."""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

from .performance_tracker import BenchmarkSuite


@dataclass
class ComparisonMetrics:
    """Comparison metrics between monolith and microservices."""

    # LLM call reduction
    llm_calls_reduction: float  # Percentage reduction

    # Speed improvement
    speed_improvement: float  # Percentage improvement

    # Cache effectiveness
    cache_hit_rate: float

    # Success rate
    success_rate: float

    # Quality metrics
    avg_tasks_per_complex: float
    avg_depth: float


class ComparisonAnalyzer:
    """Analyzes benchmark results against baseline expectations."""

    # Baseline expectations from microservices architecture
    MICROSERVICES_BASELINE = {
        "simple": {
            "avg_llm_calls": 3.5,  # Complexity + atomicity + implementation details
            "avg_time": 2.5,  # Network hops + service coordination
            "cache_hit_rate": 0.1,  # Limited caching
        },
        "medium": {
            "avg_llm_calls": 8.0,  # Multiple analysis + decomposition rounds
            "avg_time": 6.0,  # More network hops
            "cache_hit_rate": 0.15,  # Some pattern recognition
        },
        "complex": {
            "avg_llm_calls": 15.0,  # Deep decomposition tree
            "avg_time": 12.0,  # Many service interactions
            "cache_hit_rate": 0.2,  # Template matching
        }
    }

    # Target improvements for monolith refactor
    TARGET_IMPROVEMENTS = {
        "llm_call_reduction": 0.55,  # 55% reduction
        "speed_improvement": 0.50,   # 50% faster
        "cache_hit_rate": 0.35,      # 35% cache hit rate
        "success_rate": 0.95,        # 95% success rate
    }

    def __init__(self, benchmark_suite: BenchmarkSuite):
        self.suite = benchmark_suite

    def analyze_llm_efficiency(self) -> Dict[str, Any]:
        """Analyze LLM call reduction."""
        results = {}

        for task_type in ["simple", "medium", "complex"]:
            current_stats = self.suite.get_stats_by_type(task_type)
            baseline = self.MICROSERVICES_BASELINE[task_type]

            if current_stats["count"] > 0:
                current_calls = current_stats["avg_llm_calls"]
                baseline_calls = baseline["avg_llm_calls"]
                reduction = (baseline_calls - current_calls) / baseline_calls

                results[task_type] = {
                    "current_avg_calls": current_calls,
                    "baseline_avg_calls": baseline_calls,
                    "reduction_percentage": reduction,
                    "meets_target": reduction >= self.TARGET_IMPROVEMENTS["llm_call_reduction"]
                }

        # Overall reduction
        overall_current = self.suite.get_overall_stats()["avg_llm_calls"]
        overall_baseline = sum(self.MICROSERVICES_BASELINE[t]["avg_llm_calls"] for t in ["simple", "medium", "complex"]) / 3
        overall_reduction = (overall_baseline - overall_current) / overall_baseline

        results["overall"] = {
            "current_avg_calls": overall_current,
            "baseline_avg_calls": overall_baseline,
            "reduction_percentage": overall_reduction,
            "meets_target": overall_reduction >= self.TARGET_IMPROVEMENTS["llm_call_reduction"]
        }

        return results

    def analyze_speed_improvement(self) -> Dict[str, Any]:
        """Analyze processing speed improvements."""
        results = {}

        for task_type in ["simple", "medium", "complex"]:
            current_stats = self.suite.get_stats_by_type(task_type)
            baseline = self.MICROSERVICES_BASELINE[task_type]

            if current_stats["count"] > 0:
                current_time = current_stats["avg_time"]
                baseline_time = baseline["avg_time"]
                improvement = (baseline_time - current_time) / baseline_time

                results[task_type] = {
                    "current_avg_time": current_time,
                    "baseline_avg_time": baseline_time,
                    "improvement_percentage": improvement,
                    "meets_target": improvement >= self.TARGET_IMPROVEMENTS["speed_improvement"]
                }

        # Overall improvement
        overall_current = self.suite.get_overall_stats()["avg_time"]
        overall_baseline = sum(self.MICROSERVICES_BASELINE[t]["avg_time"] for t in ["simple", "medium", "complex"]) / 3
        overall_improvement = (overall_baseline - overall_current) / overall_baseline

        results["overall"] = {
            "current_avg_time": overall_current,
            "baseline_avg_time": overall_baseline,
            "improvement_percentage": overall_improvement,
            "meets_target": overall_improvement >= self.TARGET_IMPROVEMENTS["speed_improvement"]
        }

        return results

    def analyze_cache_effectiveness(self) -> Dict[str, Any]:
        """Analyze cache hit rates."""
        results = {}

        for task_type in ["simple", "medium", "complex"]:
            current_stats = self.suite.get_stats_by_type(task_type)
            baseline = self.MICROSERVICES_BASELINE[task_type]

            if current_stats["count"] > 0:
                current_rate = current_stats["cache_hit_rate"]
                baseline_rate = baseline["cache_hit_rate"]
                improvement = current_rate - baseline_rate

                results[task_type] = {
                    "current_hit_rate": current_rate,
                    "baseline_hit_rate": baseline_rate,
                    "improvement": improvement,
                    "meets_target": current_rate >= self.TARGET_IMPROVEMENTS["cache_hit_rate"]
                }

        # Overall cache effectiveness
        overall_rate = self.suite.get_overall_stats()["overall_cache_hit_rate"]

        results["overall"] = {
            "current_hit_rate": overall_rate,
            "target_hit_rate": self.TARGET_IMPROVEMENTS["cache_hit_rate"],
            "meets_target": overall_rate >= self.TARGET_IMPROVEMENTS["cache_hit_rate"]
        }

        return results

    def generate_comparison_report(self) -> Dict[str, Any]:
        """Generate comprehensive comparison report."""

        llm_analysis = self.analyze_llm_efficiency()
        speed_analysis = self.analyze_speed_improvement()
        cache_analysis = self.analyze_cache_effectiveness()
        overall_stats = self.suite.get_overall_stats()

        # Calculate overall success metrics
        target_met_count = 0
        total_targets = 4

        if llm_analysis["overall"]["meets_target"]:
            target_met_count += 1
        if speed_analysis["overall"]["meets_target"]:
            target_met_count += 1
        if cache_analysis["overall"]["meets_target"]:
            target_met_count += 1
        if overall_stats["success_rate"] >= self.TARGET_IMPROVEMENTS["success_rate"]:
            target_met_count += 1

        report = {
            "summary": {
                "targets_met": f"{target_met_count}/{total_targets}",
                "overall_success": target_met_count >= 3,  # At least 3/4 targets
                "recommendation": self._get_recommendation(target_met_count, total_targets)
            },
            "llm_efficiency": llm_analysis,
            "speed_improvement": speed_analysis,
            "cache_effectiveness": cache_analysis,
            "quality_metrics": {
                "success_rate": overall_stats["success_rate"],
                "target_success_rate": self.TARGET_IMPROVEMENTS["success_rate"],
                "meets_target": overall_stats["success_rate"] >= self.TARGET_IMPROVEMENTS["success_rate"],
                "avg_tasks_per_run": overall_stats["avg_tasks_per_run"]
            },
            "targets": self.TARGET_IMPROVEMENTS,
            "baseline": self.MICROSERVICES_BASELINE
        }

        return report

    def _get_recommendation(self, targets_met: int, total_targets: int) -> str:
        """Get recommendation based on target achievement."""
        if targets_met == total_targets:
            return "EXCELLENT: All optimization targets achieved. Ready for production deployment."
        elif targets_met >= total_targets * 0.75:
            return "GOOD: Most targets achieved. Minor optimizations recommended before deployment."
        elif targets_met >= total_targets * 0.5:
            return "FAIR: Some targets achieved. Significant optimizations needed before deployment."
        else:
            return "POOR: Few targets achieved. Major refactoring needed before deployment."

    def print_comparison_report(self):
        """Print detailed comparison report."""
        report = self.generate_comparison_report()

        print("\n" + "="*80)
        print("MONOLITH vs MICROSERVICES PERFORMANCE COMPARISON")
        print("="*80)

        # Summary
        summary = report["summary"]
        print(f"\nOVERALL ASSESSMENT: {summary['recommendation']}")
        print(f"Targets Met: {summary['targets_met']}")

        # LLM Efficiency
        print(f"\n{'LLM CALL REDUCTION':<30} {'Current':<12} {'Baseline':<12} {'Reduction':<12} {'Target Met'}")
        print("-" * 80)
        llm_data = report["llm_efficiency"]
        for task_type in ["simple", "medium", "complex", "overall"]:
            if task_type in llm_data:
                data = llm_data[task_type]
                status = "✓" if data["meets_target"] else "✗"
                print(f"{task_type.capitalize():<30} {data['current_avg_calls']:<12.1f} {data['baseline_avg_calls']:<12.1f} {data['reduction_percentage']:<12.1%} {status}")

        # Speed Improvement
        print(f"\n{'SPEED IMPROVEMENT':<30} {'Current (s)':<12} {'Baseline (s)':<12} {'Improvement':<12} {'Target Met'}")
        print("-" * 80)
        speed_data = report["speed_improvement"]
        for task_type in ["simple", "medium", "complex", "overall"]:
            if task_type in speed_data:
                data = speed_data[task_type]
                status = "✓" if data["meets_target"] else "✗"
                print(f"{task_type.capitalize():<30} {data['current_avg_time']:<12.1f} {data['baseline_avg_time']:<12.1f} {data['improvement_percentage']:<12.1%} {status}")

        # Cache Effectiveness
        print(f"\n{'CACHE EFFECTIVENESS':<30} {'Hit Rate':<12} {'Target':<12} {'Status'}")
        print("-" * 50)
        cache_data = report["cache_effectiveness"]
        overall_cache = cache_data["overall"]
        status = "✓" if overall_cache["meets_target"] else "✗"
        print(f"{'Overall Cache Hit Rate':<30} {overall_cache['current_hit_rate']:<12.1%} {overall_cache['target_hit_rate']:<12.1%} {status}")

        # Quality Metrics
        print(f"\n{'QUALITY METRICS':<30} {'Current':<12} {'Target':<12} {'Status'}")
        print("-" * 50)
        quality = report["quality_metrics"]
        status = "✓" if quality["meets_target"] else "✗"
        print(f"{'Success Rate':<30} {quality['success_rate']:<12.1%} {quality['target_success_rate']:<12.1%} {status}")
        print(f"{'Avg Tasks per Run':<30} {quality['avg_tasks_per_run']:<12.1f}")

    def export_comparison_report(self, filepath: str):
        """Export comparison report to JSON."""
        report = self.generate_comparison_report()

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)


class HistoricalComparison:
    """Compare current results with historical benchmark data."""

    def __init__(self, current_suite: BenchmarkSuite):
        self.current_suite = current_suite

    def load_historical_data(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Load historical benchmark data."""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def compare_with_historical(self, historical_filepath: str) -> Optional[Dict[str, Any]]:
        """Compare current results with historical data."""
        historical = self.load_historical_data(historical_filepath)
        if not historical:
            return None

        current_stats = self.current_suite.get_overall_stats()
        historical_stats = historical.get("overall_stats", {})

        comparison = {
            "time_delta": {
                "current": current_stats.get("avg_time", 0),
                "historical": historical_stats.get("avg_time", 0),
                "improvement": self._calculate_improvement(
                    historical_stats.get("avg_time", 0),
                    current_stats.get("avg_time", 0)
                )
            },
            "llm_efficiency_delta": {
                "current": current_stats.get("avg_llm_calls", 0),
                "historical": historical_stats.get("avg_llm_calls", 0),
                "improvement": self._calculate_improvement(
                    historical_stats.get("avg_llm_calls", 0),
                    current_stats.get("avg_llm_calls", 0)
                )
            },
            "cache_delta": {
                "current": current_stats.get("overall_cache_hit_rate", 0),
                "historical": historical_stats.get("overall_cache_hit_rate", 0),
                "improvement": current_stats.get("overall_cache_hit_rate", 0) - historical_stats.get("overall_cache_hit_rate", 0)
            }
        }

        return comparison

    def _calculate_improvement(self, old_value: float, new_value: float) -> float:
        """Calculate improvement percentage (negative means degradation)."""
        if old_value == 0:
            return 0.0
        return (old_value - new_value) / old_value