"""Tests for performance analyzer."""
import pytest
from src.utils.performance_analyzer import PerformanceAnalyzer

def test_analyze_code():
    """Test code analysis."""
    analyzer = PerformanceAnalyzer()
    
    # Test simple function
    simple_code = """
def simple_function(x):
    if x > 0:
        return x
    return 0
"""
    simple_result = analyzer.analyze_code(simple_code)
    assert "complexity_metrics" in simple_result
    assert simple_result["complexity_metrics"]["cyclomatic_complexity"] > 1  # Has at least one branch
    assert simple_result["complexity_metrics"]["cognitive_complexity"] >= 1  # Has some complexity
    
    # Test nested conditions
    nested_code = """
def complex_function(x, y):
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    else:
        if y < 0:
            return -x - y
        else:
            return -x + y
"""
    nested_result = analyzer.analyze_code(nested_code)
    # More complex than simple function
    assert nested_result["complexity_metrics"]["cyclomatic_complexity"] > simple_result["complexity_metrics"]["cyclomatic_complexity"]
    assert nested_result["complexity_metrics"]["cognitive_complexity"] > simple_result["complexity_metrics"]["cognitive_complexity"]
    
    # Test loops and error handling
    complex_code = """
def process_data(data):
    result = 0
    try:
        for item in data:
            while item > 0:
                result += 1
                item -= 1
    except ValueError:
        return 0
    return result
"""
    complex_result = analyzer.analyze_code(complex_code)
    # More complex than nested conditions due to loops and error handling
    assert complex_result["complexity_metrics"]["cyclomatic_complexity"] > simple_result["complexity_metrics"]["cyclomatic_complexity"]
    assert complex_result["complexity_metrics"]["cognitive_complexity"] > simple_result["complexity_metrics"]["cognitive_complexity"] 