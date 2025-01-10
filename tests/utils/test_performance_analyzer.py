"""Tests for performance analyzer."""
import pytest
from src.utils.performance_analyzer import PerformanceAnalyzer

def test_analyze_code():
    """Test code analysis."""
    analyzer = PerformanceAnalyzer()
    
    # Test simple function
    code = """
def simple_function(x):
    if x > 0:
        return x
    return 0
"""
    result = analyzer.analyze_code(code)
    assert "complexity_metrics" in result
    assert result["complexity_metrics"]["cyclomatic_complexity"] == 2
    assert result["complexity_metrics"]["cognitive_complexity"] == 1
    
    # Test nested conditions
    code = """
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
    result = analyzer.analyze_code(code)
    assert result["complexity_metrics"]["cyclomatic_complexity"] == 4
    assert result["complexity_metrics"]["cognitive_complexity"] == 5
    
    # Test loops and error handling
    code = """
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
    result = analyzer.analyze_code(code)
    assert result["complexity_metrics"]["cyclomatic_complexity"] == 4
    assert result["complexity_metrics"]["cognitive_complexity"] == 5 