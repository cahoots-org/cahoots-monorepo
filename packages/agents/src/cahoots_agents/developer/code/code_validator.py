"""Code validation functionality for the developer agent."""
from typing import Dict, Any, List
import logging
import json
import ast

from src.models.task import Task
from src.utils.metrics import MetricsCollector
from src.validation.policy_chain import ValidationChain, ValidationContext
from src.validation.rule_validator import create_default_validator, RuleContext
from src.recognition.pattern_detector import create_default_recognizer

class CodeValidator:
    """Handles code validation."""
    
    def __init__(self, agent):
        """Initialize the code validator.
        
        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)
        
        # Initialize validation components
        self.validation_chain = ValidationChain.create_default_chain()
        self.rule_validator = create_default_validator()
        self.pattern_recognizer = create_default_recognizer()
        self.metrics_collector = MetricsCollector()
        
    async def validate_implementation(self, code: str, task: Task) -> Dict[str, Any]:
        """Validate implementation against quality standards.
        
        Args:
            code: The implementation code to validate
            task: The task being implemented
            
        Returns:
            Dict[str, Any]: Validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "metrics": {},
            "patterns": []
        }
        
        # Track validation time
        with self.metrics_collector.track_time("validation_duration"):
            # Run automated validation first
            automated_results = self._run_automated_validation(code, task)
            results["errors"].extend(automated_results["errors"])
            results["warnings"].extend(automated_results["warnings"])
            results["metrics"].update(automated_results["metrics"])
            results["patterns"].extend(automated_results["patterns"])
            
            # Run LLM validation for higher-level checks
            llm_results = await self._run_llm_validation(code, task)
            results["errors"].extend(llm_results.get("errors", []))
            
            # Update validity based on errors
            results["valid"] = len(results["errors"]) == 0
            
            # Record metrics
            self.metrics_collector.record_counter(
                "validation_errors", 
                len(results["errors"])
            )
            self.metrics_collector.record_counter(
                "validation_warnings", 
                len(results["warnings"])
            )
            
        return results
        
    def _run_automated_validation(self, code: str, task: Task) -> Dict[str, Any]:
        """Run automated validation checks.
        
        Args:
            code: Code to validate
            task: Task being implemented
            
        Returns:
            Dict[str, Any]: Validation results
        """
        results = {
            "errors": [],
            "warnings": [],
            "metrics": {},
            "patterns": []
        }
        
        try:
            # Basic syntax check
            ast.parse(code)
            
            # Run validation chain
            validation_context = ValidationContext(
                code=code,
                file_path=task.file_path if hasattr(task, 'file_path') else "",
                language="python",
                metadata={"task_id": task.id, "requirements": task.requirements}
            )
            chain_issues = self.validation_chain.validate(validation_context)
            results["warnings"].extend(chain_issues)
            
            # Run rule validation
            rule_context = RuleContext(
                code=code,
                file_path=task.file_path if hasattr(task, 'file_path') else "",
                metadata={"task_id": task.id}
            )
            rule_issues = self.rule_validator.validate(rule_context)
            for issue in rule_issues:
                if issue.startswith("error:"):
                    results["errors"].append(issue)
                else:
                    results["warnings"].append(issue)
                    
            # Detect patterns
            patterns = self.pattern_recognizer.analyze(code, task.file_path if hasattr(task, 'file_path') else "")
            results["patterns"] = [
                {
                    "name": p.name,
                    "description": p.description,
                    "confidence": p.confidence,
                    "location": p.location
                }
                for p in patterns
            ]
            
            # Calculate metrics
            results["metrics"] = self._calculate_metrics(code)
            
        except SyntaxError as e:
            results["errors"].append(f"Syntax error: {str(e)}")
            
        return results
        
    async def _run_llm_validation(self, code: str, task: Task) -> Dict[str, Any]:
        """Run LLM-based validation for higher-level checks.
        
        Args:
            code: Code to validate
            task: Task being implemented
            
        Returns:
            Dict[str, Any]: Validation results
        """
        validation_prompt = f"""Validate this implementation focusing on high-level aspects:
        Code:
        {code}
        
        Task:
        {task.title}
        {task.description}
        
        Focus on these aspects:
        1. SOLID principles
        2. Design patterns appropriateness
        3. Architecture consistency
        4. Business logic correctness
        5. Edge case handling
        6. Security considerations
        7. Performance implications
        
        Respond with:
        {{
            "errors": []  // List of high-level issues found
        }}
        """
        
        validation_response = await self.agent.generate_response(validation_prompt)
        
        try:
            return json.loads(validation_response)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse validation response: {str(e)}")
            return {"errors": ["Failed to parse validation response"]}
            
    def _calculate_metrics(self, code: str) -> Dict[str, Any]:
        """Calculate code quality metrics.
        
        Args:
            code: Code to analyze
            
        Returns:
            Dict[str, Any]: Code metrics
        """
        tree = ast.parse(code)
        
        metrics = {
            "loc": len(code.split("\n")),
            "classes": 0,
            "functions": 0,
            "docstring_coverage": 0,
            "type_hint_coverage": 0,
            "complexity": 0
        }
        
        # Count nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
            elif isinstance(node, ast.FunctionDef):
                metrics["functions"] += 1
                # Basic complexity = number of branches
                metrics["complexity"] += len([n for n in ast.walk(node) 
                                           if isinstance(n, (ast.If, ast.For, ast.While))])
                
        return metrics 