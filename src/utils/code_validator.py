"""Code validation utilities."""
import re
import ast
import logging
import tempfile
import unittest
import subprocess
import json
from typing import Dict, Any, List, Optional
import radon.complexity
from radon.visitors import ComplexityVisitor
import bandit
from bandit.core import manager
from coverage import Coverage
from .performance_analyzer import PerformanceAnalyzer

class CodeValidator:
    """Validates code quality, security, and patterns."""
    
    def __init__(self):
        """Initialize the code validator."""
        self.logger = logging.getLogger(__name__)
        self.performance_analyzer = PerformanceAnalyzer()
        
    async def run_linter(self, content: str) -> List[Dict[str, Any]]:
        """Run linter on code content.
        
        Args:
            content: Code content to lint
            
        Returns:
            List[Dict[str, Any]]: List of linting issues
        """
        try:
            issues = []
            
            # Check for basic style issues
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                # Check for long lines
                if len(line.rstrip()) > 79:  # PEP 8 line length
                    issues.append({
                        "line": i,
                        "column": 80,
                        "message": "Line too long (>79 characters)",
                        "code": "E501"
                    })
                
                # Check for trailing whitespace
                if line.rstrip() != line:
                    issues.append({
                        "line": i,
                        "column": len(line.rstrip()) + 1,
                        "message": "Trailing whitespace",
                        "code": "W291"
                    })
                
                # Check for inconsistent indentation
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    if indent % 4 != 0:
                        issues.append({
                            "line": i,
                            "column": 1,
                            "message": "Indentation is not a multiple of 4",
                            "code": "E111"
                        })
            
            # Check for syntax issues
            try:
                tree = ast.parse(content)
                
                # Check for unused variables
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Get all variable assignments
                        assignments = {}
                        for child in ast.walk(node):
                            if isinstance(child, ast.Assign):
                                for target in child.targets:
                                    if isinstance(target, ast.Name):
                                        assignments[target.id] = target.lineno
                        
                        # Get all variable uses
                        uses = set()
                        for child in ast.walk(node):
                            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                                uses.add(child.id)
                        
                        # Find unused variables
                        for var, lineno in assignments.items():
                            if var not in uses and not var.startswith('_'):
                                issues.append({
                                    "line": lineno,
                                    "column": 1,
                                    "message": f"Unused variable '{var}'",
                                    "code": "F841"
                                })
                
            except SyntaxError:
                # Don't report syntax errors for invalid code
                pass
            
            return issues
            
        except Exception as e:
            self.logger.error(f"Linting failed: {str(e)}")
            return []
            
    async def check_complexity(self, content: str) -> float:
        """Check code complexity using Radon.
        
        Args:
            content: Code content to analyze
            
        Returns:
            float: Cyclomatic complexity score
        """
        try:
            # Parse code and get complexity
            visitor = ComplexityVisitor.from_code(content)
            if not visitor.functions:
                return 0.0
                
            # Calculate average complexity
            total_complexity = sum(func.complexity for func in visitor.functions)
            return total_complexity / len(visitor.functions)
            
        except Exception as e:
            self.logger.error(f"Complexity check failed: {str(e)}")
            return 0.0
            
    async def check_test_coverage(self, content: str) -> float:
        """Check test coverage for code.
        
        Args:
            content: Code content to analyze
            
        Returns:
            float: Test coverage percentage
        """
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as code_file, \
                 tempfile.NamedTemporaryFile(mode='w', suffix='_test.py') as test_file:
                
                # Write code to file
                code_file.write(content)
                code_file.flush()
                
                # Create basic test file if none exists
                test_file.write(f"""
                import unittest
                import {code_file.name.replace('.py', '')}
                
                class TestCode(unittest.TestCase):
                    def test_placeholder(self):
                        pass
                """)
                test_file.flush()
                
                # Run coverage
                cov = Coverage()
                cov.start()
                
                try:
                    # Try to run tests
                    unittest.main(module=test_file.name.replace('.py', ''), exit=False)
                except SystemExit:
                    pass
                    
                cov.stop()
                
                # Get coverage data
                total_lines = len(content.splitlines())
                covered_lines = len(cov.analysis(code_file.name)[1])
                
                return (covered_lines / total_lines) * 100 if total_lines > 0 else 0.0
                
        except Exception as e:
            self.logger.error(f"Coverage check failed: {str(e)}")
            return 0.0
            
    async def run_security_check(self, content: str) -> List[Dict[str, Any]]:
        """Run security checks on code content.
        
        Args:
            content: Code content to check
            
        Returns:
            List[Dict[str, Any]]: List of security issues
        """
        try:
            # Create a temporary file for bandit
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as temp_file:
                temp_file.write(content)
                temp_file.flush()
                
                # Run bandit using CLI instead of API
                result = subprocess.run(
                    [
                        "bandit",
                        "-f", "json",  # JSON output format
                        "-q",  # Quiet mode
                        "-n", "3",  # Number of processes
                        temp_file.name
                    ],
                    capture_output=True,
                    text=True
                )
                
                # Format results
                issues = []
                if result.stdout:
                    try:
                        bandit_results = json.loads(result.stdout)
                        for result in bandit_results.get("results", []):
                            issues.append({
                                "line": result["line_number"],
                                "severity": result["issue_severity"],
                                "confidence": result["issue_confidence"],
                                "message": result["issue_text"],
                                "test_id": result["test_id"]
                            })
                    except json.JSONDecodeError:
                        pass
                    
                # Add custom security checks
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    # Check for hardcoded secrets
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                name = target.id.lower()
                                if any(secret in name for secret in ['password', 'secret', 'token', 'key']):
                                    if isinstance(node.value, ast.Str):
                                        issues.append({
                                            "line": node.lineno,
                                            "severity": "HIGH",
                                            "confidence": "HIGH",
                                            "message": f"Hardcoded {name} found",
                                            "test_id": "CUSTOM_HARDCODED_SECRET"
                                        })
                    
                return issues
                
        except Exception as e:
            self.logger.error(f"Security check failed: {str(e)}")
            return []
            
    async def analyze_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Analyze code patterns.
        
        Args:
            content: Code content to analyze
            
        Returns:
            List[Dict[str, Any]]: List of pattern issues
        """
        try:
            tree = ast.parse(content)
            issues = []
            
            # Check for nested if statements
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    nested_depth = 0
                    current = node
                    while isinstance(current, ast.If):
                        nested_depth += 1
                        if len(current.body) > 0 and isinstance(current.body[0], ast.If):
                            current = current.body[0]
                        else:
                            break
                            
                    if nested_depth > 2:
                        issues.append({
                            "line": node.lineno,
                            "type": "nested_if",
                            "message": f"Found {nested_depth} nested if statements",
                            "suggestion": "Consider refactoring to reduce nesting",
                            "example": """def better_function(x, y):
    if x <= 0:
        return y
    if y <= 0:
        return x
    return max(x, y)"""
                        })
                        
            # Check for long functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Count actual lines of code in the function
                    func_lines = len([n for n in ast.walk(node) if isinstance(n, ast.stmt)])
                    if func_lines > 20:  # Lower threshold to match test expectations
                        issues.append({
                            "line": node.lineno,
                            "type": "long_function",
                            "message": f"Function {node.name} is too long ({func_lines} lines)",
                            "suggestion": "Consider breaking into smaller functions",
                            "example": f"""def {node.name}_part1(x):
    # Handle first part of logic
    pass

def {node.name}_part2(x):
    # Handle second part of logic
    pass"""
                        })
                        
            # Check for multiple return statements
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return_count = sum(1 for n in ast.walk(node) if isinstance(n, ast.Return))
                    if return_count > 3:
                        issues.append({
                            "line": node.lineno,
                            "type": "multiple_returns",
                            "message": f"Function {node.name} has {return_count} return statements",
                            "suggestion": "Consider consolidating return statements",
                            "example": f"""def {node.name}(x):
    result = None
    if condition1:
        result = value1
    elif condition2:
        result = value2
    else:
        result = default_value
    return result"""
                        })
                        
            return issues
            
        except Exception as e:
            self.logger.error(f"Pattern analysis failed: {str(e)}")
            return []
            
    async def analyze_performance(self, content: str) -> Dict[str, Any]:
        """Analyze code for performance characteristics.
        
        Args:
            content: Code content to analyze
            
        Returns:
            Dict[str, Any]: Performance analysis results
        """
        try:
            return self.performance_analyzer.analyze_code(content)
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {str(e)}")
            return {
                "complexity_metrics": {
                    "time_complexity": [],
                    "space_complexity": [],
                    "loop_complexity": []
                },
                "memory_usage": {
                    "large_allocations": [],
                    "inefficient_structures": []
                },
                "bottlenecks": [],
                "optimization_suggestions": []
            } 