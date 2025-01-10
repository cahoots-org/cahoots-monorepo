"""Shared utility functions."""
from typing import Dict, Any, List, Optional
import time
import jsonschema
from datetime import datetime

class TimeUtils:
    """Time utility functions."""
    
    @staticmethod
    def current_timestamp() -> float:
        """Get current timestamp.
        
        Returns:
            Current timestamp in seconds
        """
        return time.time()

class DataUtils:
    """Data utility functions."""
    
    @staticmethod
    def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.
        
        Args:
            dict1: First dictionary
            dict2: Second dictionary
            
        Returns:
            Merged dictionary
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUtils.deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result

class Validator:
    """Data validation utilities."""
    
    def __init__(self):
        """Initialize validator."""
        self.validator = jsonschema.Draft7Validator({})
        self._custom_rules = {}
        
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate data against JSON schema.
        
        Args:
            data: Data to validate
            schema: JSON schema
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        validator = jsonschema.Draft7Validator(schema)
        validator.validate(data)
        return True
        
    def add_validation_rule(self, name: str, rule_func: callable) -> None:
        """Add custom validation rule.
        
        Args:
            name: Rule name
            rule_func: Validation function
        """
        self._custom_rules[name] = rule_func

class MetricsCollector:
    """Metrics collection utilities."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self._counters = {}
        self._gauges = {}
        
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment counter.
        
        Args:
            name: Counter name
            value: Value to increment by
        """
        if name not in self._counters:
            self._counters[name] = 0
        self._counters[name] += value
        
    def get_counter(self, name: str) -> int:
        """Get counter value.
        
        Args:
            name: Counter name
            
        Returns:
            Counter value
        """
        return self._counters.get(name, 0)
        
    def set_gauge(self, name: str, value: float) -> None:
        """Set gauge value.
        
        Args:
            name: Gauge name
            value: Gauge value
        """
        self._gauges[name] = value
        
    def get_gauge(self, name: str) -> float:
        """Get gauge value.
        
        Args:
            name: Gauge name
            
        Returns:
            Gauge value
        """
        return self._gauges.get(name, 0.0)
        
    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        
    def export(self) -> Dict[str, Any]:
        """Export all metrics.
        
        Returns:
            Dict containing all metrics
        """
        return {
            "counters": self._counters.copy(),
            "gauges": self._gauges.copy()
        } 