"""
Test Result Parsing.

Parses test output from different frameworks into a common format:
- Jest (Node.js)
- pytest (Python)
- Go test
"""

import json
import re
from typing import Optional, List
from app.models.schemas import TestResults, TestFailure


def parse_jest_results(output: str) -> TestResults:
    """
    Parse Jest JSON output into common format.

    Jest JSON format (when run with --json):
    {
        "numPassedTests": 5,
        "numFailedTests": 1,
        "numPendingTests": 0,
        "testResults": [
            {
                "name": "/path/to/file.test.ts",
                "status": "failed",
                "startTime": 1234567890,
                "endTime": 1234567891,
                "assertionResults": [
                    {
                        "fullName": "test name",
                        "status": "failed",
                        "failureMessages": ["Error message"]
                    }
                ]
            }
        ]
    }
    """
    results = TestResults()

    try:
        # Try to parse JSON from output
        json_match = re.search(r'\{[\s\S]*"numPassedTests"[\s\S]*\}', output)
        if not json_match:
            # Try finding results.json content in output
            return _parse_jest_console_output(output)

        data = json.loads(json_match.group())

        results.passed = data.get("numPassedTests", 0)
        results.failed = data.get("numFailedTests", 0)
        results.skipped = data.get("numPendingTests", 0)

        # Calculate duration from test results
        test_results = data.get("testResults", [])
        if test_results:
            start_time = min(tr.get("startTime", 0) for tr in test_results if tr.get("startTime"))
            end_time = max(tr.get("endTime", 0) for tr in test_results if tr.get("endTime"))
            if start_time and end_time:
                results.duration = (end_time - start_time) / 1000.0  # Convert ms to seconds

        # Extract failures
        for test_file in test_results:
            file_name = test_file.get("name", "")
            for assertion in test_file.get("assertionResults", []):
                if assertion.get("status") == "failed":
                    failure_messages = assertion.get("failureMessages", [])
                    error = "\n".join(failure_messages) if failure_messages else "Test failed"

                    # Try to extract line number from stack trace
                    line = _extract_line_from_jest_error(error, file_name)

                    results.failures.append(TestFailure(
                        test=assertion.get("fullName", assertion.get("title", "Unknown test")),
                        file=file_name,
                        line=line,
                        error=error[:2000]  # Truncate very long errors
                    ))

    except (json.JSONDecodeError, KeyError, TypeError):
        # Fall back to console output parsing
        return _parse_jest_console_output(output)

    return results


def _parse_jest_console_output(output: str) -> TestResults:
    """Parse Jest console output when JSON isn't available."""
    results = TestResults()

    # Match summary line: "Tests: 5 passed, 1 failed, 6 total"
    summary_match = re.search(
        r'Tests:\s*(?:(\d+)\s+passed,?\s*)?(?:(\d+)\s+failed,?\s*)?(?:(\d+)\s+skipped,?\s*)?(\d+)\s+total',
        output
    )
    if summary_match:
        results.passed = int(summary_match.group(1) or 0)
        results.failed = int(summary_match.group(2) or 0)
        results.skipped = int(summary_match.group(3) or 0)

    # Match time: "Time: 2.345 s"
    time_match = re.search(r'Time:\s*([\d.]+)\s*s', output)
    if time_match:
        results.duration = float(time_match.group(1))

    # Match failure blocks
    failure_pattern = re.compile(
        r'FAIL\s+(.+?)\n.*?●\s+(.+?)\n\s*([\s\S]*?)(?=(?:\n\s*●|\n\s*FAIL|\n\s*PASS|$))',
        re.MULTILINE
    )

    for match in failure_pattern.finditer(output):
        file_name = match.group(1).strip()
        test_name = match.group(2).strip()
        error = match.group(3).strip()

        line = _extract_line_from_jest_error(error, file_name)

        results.failures.append(TestFailure(
            test=test_name,
            file=file_name,
            line=line,
            error=error[:2000]
        ))

    return results


def _extract_line_from_jest_error(error: str, file_name: str) -> int:
    """Extract line number from Jest error stack trace."""
    # Look for pattern like "at Object.<anonymous> (file.test.ts:42:10)"
    base_name = file_name.split("/")[-1]
    pattern = rf'{re.escape(base_name)}:(\d+)'
    match = re.search(pattern, error)
    if match:
        return int(match.group(1))
    return 0


def parse_pytest_results(output: str) -> TestResults:
    """
    Parse pytest JSON output into common format.

    pytest-json-report format (when run with --json-report):
    {
        "summary": {
            "passed": 5,
            "failed": 1,
            "skipped": 0
        },
        "duration": 2.345,
        "tests": [
            {
                "nodeid": "tests/test_foo.py::test_bar",
                "outcome": "failed",
                "call": {
                    "longrepr": {
                        "reprcrash": {
                            "path": "tests/test_foo.py",
                            "lineno": 42,
                            "message": "AssertionError"
                        }
                    }
                }
            }
        ]
    }
    """
    results = TestResults()

    try:
        # Try to parse JSON from output
        json_match = re.search(r'\{[\s\S]*"summary"[\s\S]*\}', output)
        if not json_match:
            return _parse_pytest_console_output(output)

        data = json.loads(json_match.group())
        summary = data.get("summary", {})

        results.passed = summary.get("passed", 0)
        results.failed = summary.get("failed", 0)
        results.skipped = summary.get("skipped", 0)
        results.duration = data.get("duration", 0.0)

        # Extract failures
        for test in data.get("tests", []):
            if test.get("outcome") == "failed":
                nodeid = test.get("nodeid", "")
                call_info = test.get("call", {})
                longrepr = call_info.get("longrepr", {})

                if isinstance(longrepr, dict):
                    reprcrash = longrepr.get("reprcrash", {})
                    file_path = reprcrash.get("path", nodeid.split("::")[0])
                    line = reprcrash.get("lineno", 0)
                    message = reprcrash.get("message", "Test failed")
                else:
                    file_path = nodeid.split("::")[0]
                    line = 0
                    message = str(longrepr)[:2000] if longrepr else "Test failed"

                results.failures.append(TestFailure(
                    test=nodeid,
                    file=file_path,
                    line=line,
                    error=message
                ))

    except (json.JSONDecodeError, KeyError, TypeError):
        return _parse_pytest_console_output(output)

    return results


def _parse_pytest_console_output(output: str) -> TestResults:
    """Parse pytest console output when JSON isn't available."""
    results = TestResults()

    # Match summary line: "5 passed, 1 failed, 2 skipped in 2.34s"
    summary_match = re.search(
        r'(?:(\d+)\s+passed)?(?:,?\s*(\d+)\s+failed)?(?:,?\s*(\d+)\s+skipped)?.*?in\s+([\d.]+)s',
        output
    )
    if summary_match:
        results.passed = int(summary_match.group(1) or 0)
        results.failed = int(summary_match.group(2) or 0)
        results.skipped = int(summary_match.group(3) or 0)
        results.duration = float(summary_match.group(4))

    # Match FAILED tests
    failed_pattern = re.compile(r'FAILED\s+(.+?)::', re.MULTILINE)
    for match in failed_pattern.finditer(output):
        file_path = match.group(1).strip()

        # Try to find more details
        results.failures.append(TestFailure(
            test=file_path,
            file=file_path.split("::")[0],
            line=0,
            error="Test failed (see logs for details)"
        ))

    return results


def parse_go_test_results(output: str) -> TestResults:
    """Parse Go test output into common format."""
    results = TestResults()

    # Match summary line: "ok  	package	1.234s"
    # or "FAIL	package	1.234s"
    lines = output.split("\n")

    for line in lines:
        # Count passes: "--- PASS: TestName"
        if line.strip().startswith("--- PASS:"):
            results.passed += 1
        # Count failures: "--- FAIL: TestName"
        elif line.strip().startswith("--- FAIL:"):
            results.failed += 1
            # Extract test name
            match = re.match(r'--- FAIL:\s+(\S+)', line.strip())
            if match:
                test_name = match.group(1)
                results.failures.append(TestFailure(
                    test=test_name,
                    file="",  # Go doesn't report file in default output
                    line=0,
                    error="Test failed (see logs)"
                ))
        # Count skips: "--- SKIP: TestName"
        elif line.strip().startswith("--- SKIP:"):
            results.skipped += 1

    # Match total time: "ok  	package	1.234s" or "FAIL	package	1.234s"
    time_match = re.search(r'(?:ok|FAIL)\s+\S+\s+([\d.]+)s', output)
    if time_match:
        results.duration = float(time_match.group(1))

    return results


def parse_test_results(output: str, framework: str) -> TestResults:
    """Parse test results based on framework type."""
    if framework in ("jest", "node", "javascript", "typescript"):
        return parse_jest_results(output)
    elif framework in ("pytest", "python"):
        return parse_pytest_results(output)
    elif framework in ("go", "golang"):
        return parse_go_test_results(output)
    else:
        # Try to detect framework from output
        if '"numPassedTests"' in output or 'PASS' in output and 'Tests:' in output:
            return parse_jest_results(output)
        elif 'passed' in output and 'failed' in output and 'in' in output:
            return parse_pytest_results(output)
        elif '--- PASS:' in output or '--- FAIL:' in output:
            return parse_go_test_results(output)
        else:
            # Return empty results if we can't parse
            return TestResults()
