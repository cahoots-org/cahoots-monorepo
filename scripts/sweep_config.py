#!/usr/bin/env python3
"""
Automated Parameter Sweep Script for Prompt Tuning

This script systematically tests each configuration parameter one at a time,
measures results, and locks in the best value before moving to the next parameter.
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Any
import time

# Test configuration
ATOMIC_TESTS_ONLY = False  # Test all complexity levels
CONFIG_FILE = Path("/home/rmiller/cahoots-monorepo/app/config/decomposition_config.py")
RESULTS_DIR = Path("/tmp/sweep_results")
RESULTS_DIR.mkdir(exist_ok=True)

# Parameter sweep definitions
SWEEP_PARAMS = [
    {
        "name": "story_generation_temperature",
        "values": [0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15, 0.20],
        "type": "float",
        "line_pattern": r'story_generation_temperature: float = Field\(\s*default=([\d.]+)',
    },
    {
        "name": "task_decomposition_temperature",
        "values": [0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12],
        "type": "float",
        "line_pattern": r'task_decomposition_temperature: float = Field\(\s*default=([\d.]+)',
    },
    {
        "name": "task_sizing_guidance",
        "values": ["consolidated", "balanced", "granular"],
        "type": "string",
        "line_pattern": r'task_sizing_guidance: str = Field\(\s*default="(\w+)"',
    },
    {
        "name": "story_detail_level",
        "values": ["high_level", "balanced", "detailed"],
        "type": "string",
        "line_pattern": r'story_detail_level: str = Field\(\s*default="(\w+)"',
    },
    {
        "name": "implementation_focus",
        "values": ["practical", "technical", "architectural"],
        "type": "string",
        "line_pattern": r'implementation_focus: str = Field\(\s*default="(\w+)"',
    },
    {
        "name": "emphasize_consolidation",
        "values": [True, False],
        "type": "bool",
        "line_pattern": r'emphasize_consolidation: bool = Field\(\s*default=(True|False)',
    },
    {
        "name": "emphasize_feature_completeness",
        "values": [True, False],
        "type": "bool",
        "line_pattern": r'emphasize_feature_completeness: bool = Field\(\s*default=(True|False)',
    },
    {
        "name": "atomic_guidance",
        "values": ["treat_as_single_feature", "minimal_breakdown", "standard"],
        "type": "string",
        "line_pattern": r'atomic_guidance: str = Field\(\s*default="(\w+)"',
    },
]


def update_config_value(param_name: str, value: Any, line_pattern: str, value_type: str):
    """Update a single parameter in the config file."""
    content = CONFIG_FILE.read_text()

    if value_type == "string":
        replacement = f'default="{value}"'
    elif value_type == "bool":
        replacement = f'default={value}'
    elif value_type == "float":
        replacement = f'default={value}'

    # Find and replace the default value
    pattern = re.compile(line_pattern)
    new_content = pattern.sub(lambda m: m.group(0).replace(f'default={m.group(1)}' if value_type != "string" else f'default="{m.group(1)}"', replacement), content)

    CONFIG_FILE.write_text(new_content)
    print(f"  ✓ Updated {param_name} = {value}")


def rebuild_api():
    """Rebuild the Docker API service."""
    print("  Rebuilding API...")
    result = subprocess.run(
        ["docker", "compose", "up", "--build", "-d", "api"],
        capture_output=True,
        text=True,
        cwd="/home/rmiller/cahoots-monorepo"
    )
    if result.returncode != 0:
        print(f"  ✗ Build failed: {result.stderr}")
        return False
    print("  ✓ API rebuilt")

    # Wait for API health check
    print("  Waiting for API health check...")
    max_wait = 60
    for i in range(max_wait):
        result = subprocess.run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", "cahoots-monorepo-api-1"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and "healthy" in result.stdout:
            print("  ✓ API ready")
            return True
        time.sleep(1)

    print(f"  ✗ API health check timeout")
    return False


def run_validation():
    """Run lightweight validation suite (1 test per complexity level)."""
    print("  Running lightweight validation...")
    validation_start = time.time()

    # Use lightweight validation suite (4 tests total: 1 per complexity level)
    result = subprocess.run(
        ["./scripts/validation_suite_light.sh", "all"],
        capture_output=True,
        text=True,
        cwd="/home/rmiller/cahoots-monorepo",
        timeout=1200  # 20 minutes max
    )

    validation_time = time.time() - validation_start

    # Parse JSON report from lightweight validation suite
    report_file = Path("/tmp/validation_report_light.json")
    if not report_file.exists():
        print(f"  ✗ Report file not found: {report_file}")
        return None

    try:
        with open(report_file) as f:
            report = json.load(f)
    except Exception as e:
        print(f"  ✗ Failed to parse report: {e}")
        return None

    if not report:
        print(f"  ✗ No test results in report")
        return None

    # Calculate metrics
    total_tests = len(report)
    passed = sum(1 for r in report if r.get('success', False))
    pass_rate = passed / total_tests if total_tests else 0

    # Get task counts
    all_tasks = [r.get('tasks', 0) for r in report if r.get('tasks')]
    avg_tasks = sum(all_tasks) / len(all_tasks) if all_tasks else 0

    print(f"  ✓ Results: {total_tests} tests, {passed} passed, {pass_rate:.0%} pass rate, avg {avg_tasks:.1f} tasks ({validation_time:.1f}s)")

    return {
        "tasks": all_tasks,
        "avg_tasks": avg_tasks,
        "pass_rate": pass_rate,
        "passed": passed,
        "total": total_tests,
        "validation_time": validation_time,
        "report": report
    }


def sweep_parameter(param: Dict):
    """Sweep a single parameter and return best value."""
    print(f"\n{'='*60}")
    print(f"SWEEPING: {param['name']}")
    print(f"Values: {param['values']}")
    print(f"{'='*60}")

    results = []

    for value in param['values']:
        print(f"\n[{param['name']} = {value}]")

        # Update config
        update_config_value(param['name'], value, param['line_pattern'], param['type'])

        # Rebuild
        rebuild_start = time.time()
        if not rebuild_api():
            continue
        rebuild_time = time.time() - rebuild_start

        # Run validation (no additional wait needed)
        result = run_validation()
        if result:
            total_time = rebuild_time + result.get("validation_time", 0)
            results.append({
                "value": value,
                "avg_tasks": result["avg_tasks"],
                "pass_rate": result["pass_rate"],
                "passed": result["passed"],
                "total": result["total"],
                "rebuild_time": rebuild_time,
                "validation_time": result.get("validation_time", 0),
                "total_time": total_time
            })
            print(f"  Timing: rebuild={rebuild_time:.1f}s, validation={result.get('validation_time', 0):.1f}s, total={total_time:.1f}s")

            # Save intermediate results
            result_file = RESULTS_DIR / f"{param['name']}_sweep.json"
            result_file.write_text(json.dumps(results, indent=2))

    # Find best value (highest pass rate, then lowest avg tasks)
    if not results:
        print(f"\n✗ No valid results for {param['name']}")
        return None

    best = max(results, key=lambda x: (x['pass_rate'], -x['avg_tasks']))

    print(f"\n{'='*60}")
    print(f"BEST VALUE: {param['name']} = {best['value']}")
    print(f"  Pass rate: {best['pass_rate']:.0%}")
    print(f"  Avg tasks: {best['avg_tasks']:.1f}")
    print(f"{'='*60}")

    return best['value']


def main():
    """Main sweep execution."""
    print("="*60)
    print("AUTOMATED PARAMETER SWEEP")
    print("="*60)

    locked_values = {}

    for param in SWEEP_PARAMS:
        best_value = sweep_parameter(param)

        if best_value is not None:
            locked_values[param['name']] = best_value
            # Lock in the best value
            update_config_value(param['name'], best_value, param['line_pattern'], param['type'])
            rebuild_api()
            print(f"\n✓ LOCKED: {param['name']} = {best_value}")

        # Save cumulative locked values
        locked_file = RESULTS_DIR / "locked_values.json"
        locked_file.write_text(json.dumps(locked_values, indent=2))

    print("\n" + "="*60)
    print("SWEEP COMPLETE")
    print("="*60)
    print("\nFinal Optimized Configuration:")
    for k, v in locked_values.items():
        print(f"  {k}: {v}")
    print(f"\nResults saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
