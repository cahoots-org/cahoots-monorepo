"""Tests for code validation utilities."""
import pytest
from unittest.mock import Mock, MagicMock
from src.utils.code_validator import CodeValidator

@pytest.fixture
def mock_coverage():
    """Create a mock coverage class."""
    mock_cov_instance = MagicMock()
    mock_cov_instance.analysis.return_value = (None, [], None)  # No covered lines
    
    mock_cov_cls = MagicMock()
    mock_cov_cls.return_value = mock_cov_instance
    return mock_cov_cls, mock_cov_instance

@pytest.fixture
def mock_unittest():
    """Create a mock unittest module."""
    mock_unittest = MagicMock()
    return mock_unittest

@pytest.fixture
def mock_tempfile():
    """Create a mock tempfile module."""
    mock_tempfile = MagicMock()
    mock_code_file = MagicMock()
    mock_code_file.name = "test_code.py"
    mock_test_file = MagicMock()
    mock_test_file.name = "test_test_code.py"
    
    mock_tempfile.NamedTemporaryFile.return_value.__enter__.side_effect = [
        mock_code_file,
        mock_test_file
    ]
    return mock_tempfile, mock_code_file, mock_test_file

@pytest.fixture
def validator(mock_coverage, mock_unittest, mock_tempfile):
    """Create a code validator instance with mocked dependencies."""
    mock_cov_cls, _ = mock_coverage
    mock_temp, _, _ = mock_tempfile
    return CodeValidator(
        coverage_cls=mock_cov_cls,
        unittest_module=mock_unittest,
        tempfile_module=mock_temp
    )

@pytest.mark.asyncio
async def test_run_linter(validator):
    """Test linting functionality."""
    code = """
def bad_function():
    x    = 1  # Bad indentation and trailing whitespace    
    very_long_variable_name_that_exceeds_pep8_line_length_requirements = "This line is way too long"
    unused_var = 42
    return x
"""
    results = await validator.run_linter(code)
    
    # Verify we found the expected issues
    assert len(results) > 0
    
    # Check for specific issues
    issues_found = {issue["code"]: issue for issue in results}
    
    # Should find line length issue
    assert "E501" in issues_found
    assert "Line too long" in issues_found["E501"]["message"]
    
    # Should find trailing whitespace
    assert "W291" in issues_found
    assert "Trailing whitespace" in issues_found["W291"]["message"]
    
    # Should find unused variable
    assert "F841" in issues_found
    assert "Unused variable" in issues_found["F841"]["message"]
    
    # Verify result structure
    for issue in results:
        assert "line" in issue
        assert "message" in issue
        assert "code" in issue
        assert isinstance(issue["line"], int)
        assert isinstance(issue["message"], str)
        assert isinstance(issue["code"], str)

@pytest.mark.asyncio
async def test_check_complexity(validator):
    """Test complexity checking."""
    code = """
def complex_function(x, y):
    if x > 0:
        if y > 0:
            if x > y:
                return x
            else:
                return y
        else:
            return x
    else:
        return y
"""
    complexity = await validator.check_complexity(code)
    assert isinstance(complexity, float)
    assert complexity > 0  # Complex function should have non-zero complexity

@pytest.mark.asyncio
async def test_check_test_coverage(validator, mock_coverage, mock_unittest, mock_tempfile):
    """Test coverage checking."""
    code = """
def simple_function(x):
    return x * 2
"""
    _, mock_cov = mock_coverage
    _, mock_code_file, mock_test_file = mock_tempfile
    
    coverage = await validator.check_test_coverage(code)
    
    assert isinstance(coverage, float)
    assert 0 <= coverage <= 100  # Coverage should be a percentage
    mock_cov.start.assert_called_once()
    mock_cov.stop.assert_called_once()
    mock_unittest.main.assert_called_once()
    assert mock_code_file.write.called
    assert mock_test_file.write.called

@pytest.mark.asyncio
async def test_run_security_check(validator):
    """Test security checking."""
    code = """
import os
import subprocess

def insecure_function():
    # Hardcoded secrets
    password = "my_secret_password"
    api_key = "1234567890"
    token = "abcdef"
    
    # Dangerous system calls
    os.system("rm -rf /")
    subprocess.call("echo $HOME", shell=True)
    
    # Command injection vulnerability
    user_input = input("Enter filename: ")
    os.system(f"cat {user_input}")
    
    return password
"""
    issues = await validator.run_security_check(code)
    
    # Verify we found security issues
    assert len(issues) > 0
    
    # Check for specific issues
    found_issues = {
        (issue["severity"], issue["test_id"]): issue 
        for issue in issues
    }
    
    # Should find hardcoded secrets
    assert any(
        test_id == "CUSTOM_HARDCODED_SECRET" 
        for (_, test_id) in found_issues
    )
    
    # Should find dangerous system calls
    assert any(
        "shell" in issue["message"].lower() or 
        "system" in issue["message"].lower() 
        for issue in issues
    )
    
    # Verify issue structure
    for issue in issues:
        assert "line" in issue
        assert "severity" in issue
        assert "confidence" in issue
        assert "message" in issue
        assert "test_id" in issue
        assert isinstance(issue["line"], int)
        assert isinstance(issue["severity"], str)
        assert isinstance(issue["confidence"], str)
        assert isinstance(issue["message"], str)
        assert isinstance(issue["test_id"], str)

@pytest.mark.asyncio
async def test_analyze_patterns(validator):
    """Test pattern analysis."""
    code = """
def deeply_nested_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                if x > y:
                    return x
                else:
                    return y
            else:
                return z
        else:
            return 0
    return -1

def very_long_function():
    # This function has more than 20 lines
    line1 = 1
    line2 = 2
    line3 = 3
    line4 = 4
    line5 = 5
    line6 = 6
    line7 = 7
    line8 = 8
    line9 = 9
    line10 = 10
    line11 = 11
    line12 = 12
    line13 = 13
    line14 = 14
    line15 = 15
    line16 = 16
    line17 = 17
    line18 = 18
    line19 = 19
    line20 = 20
    line21 = 21
    return sum([line1, line2, line3, line4, line5,
               line6, line7, line8, line9, line10,
               line11, line12, line13, line14, line15,
               line16, line17, line18, line19, line20, line21])

def multiple_return_function(x):
    if x < 0:
        return -1
    if x == 0:
        return 0
    if x < 10:
        return 1
    if x < 20:
        return 2
    return 3
"""
    suggestions = await validator.analyze_patterns(code)
    
    # Verify we found pattern issues
    assert len(suggestions) > 0
    
    # Check for specific issues
    issues_found = {
        suggestion["type"]: suggestion 
        for suggestion in suggestions
    }
    
    # Should find nested if statements
    assert "nested_if" in issues_found
    assert "3" in issues_found["nested_if"]["message"]  # 3 levels of nesting
    
    # Should find long function
    assert "long_function" in issues_found
    assert "23" in issues_found["long_function"]["message"]  # 23 lines including comment and return
    
    # Should find multiple returns
    assert "multiple_returns" in issues_found
    assert "5" in issues_found["multiple_returns"]["message"]  # 5 return statements
    
    # Verify suggestion structure
    for suggestion in suggestions:
        assert "type" in suggestion
        assert "line" in suggestion
        assert "message" in suggestion
        assert "suggestion" in suggestion
        assert "example" in suggestion
        assert isinstance(suggestion["type"], str)
        assert isinstance(suggestion["line"], int)
        assert isinstance(suggestion["message"], str)
        assert isinstance(suggestion["suggestion"], str)
        assert isinstance(suggestion["example"], str)

@pytest.mark.asyncio
async def test_empty_code(validator):
    """Test handling of empty code."""
    empty_code = ""
    
    # All methods should handle empty code gracefully
    assert await validator.run_linter(empty_code) == []
    assert await validator.check_complexity(empty_code) == 0.0
    assert await validator.check_test_coverage(empty_code) == 0.0
    assert await validator.run_security_check(empty_code) == []
    assert await validator.analyze_patterns(empty_code) == []

@pytest.mark.asyncio
async def test_invalid_code(validator):
    """Test handling of invalid code."""
    invalid_code = "this is not python code"
    
    # All methods should handle invalid code gracefully
    assert await validator.run_linter(invalid_code) == []
    assert await validator.check_complexity(invalid_code) == 0.0
    assert await validator.check_test_coverage(invalid_code) == 0.0
    assert await validator.run_security_check(invalid_code) == []
    assert await validator.analyze_patterns(invalid_code) == [] 