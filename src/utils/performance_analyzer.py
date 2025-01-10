"""Performance analysis utilities."""
import ast
from typing import Dict, Any, List

class PerformanceAnalyzer:
    """Analyzes code performance and complexity."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self._metrics = {}
        
    def analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze code complexity and performance.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dict containing analysis results
        """
        tree = ast.parse(code)
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        
        return {
            "complexity_metrics": {
                "cyclomatic_complexity": visitor.cyclomatic_complexity,
                "cognitive_complexity": visitor.cognitive_complexity
            }
        }

class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor for calculating code complexity metrics."""
    
    def __init__(self):
        """Initialize the visitor."""
        self.cyclomatic_complexity = 1  # Base complexity
        self.cognitive_complexity = 0
        self._nesting_level = 0
        
    def visit_If(self, node):
        """Visit If node."""
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += (1 + self._nesting_level)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1
        
    def visit_While(self, node):
        """Visit While node."""
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += (1 + self._nesting_level)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1
        
    def visit_For(self, node):
        """Visit For node."""
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += (1 + self._nesting_level)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1
        
    def visit_Try(self, node):
        """Visit Try node."""
        self.cyclomatic_complexity += len(node.handlers)
        self.cognitive_complexity += (1 + self._nesting_level)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1
        
    def visit_ExceptHandler(self, node):
        """Visit ExceptHandler node."""
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += (1 + self._nesting_level)
        self.generic_visit(node)
        
    def visit_BoolOp(self, node):
        """Visit BoolOp node."""
        self.cyclomatic_complexity += len(node.values) - 1
        self.cognitive_complexity += (1 + self._nesting_level)
        self.generic_visit(node) 