from typing import Dict
from business_rules.engine import run_all
from business_rules.variables import BaseVariables, numeric_rule_variable, string_rule_variable
from business_rules.actions import BaseActions, rule_action
from business_rules.fields import FIELD_NUMERIC

class ContextVariables(BaseVariables):
    """Variables for context selection rules."""
    
    def __init__(self, facts: Dict):
        self.facts = facts
    
    @string_rule_variable
    def status(self):
        """Get status from facts."""
        return self.facts.get('status')
    
    @string_rule_variable
    def request_type(self):
        """Get request type from facts."""
        return self.facts.get('request_type')
    
    @string_rule_variable
    def impact(self):
        """Get impact from facts."""
        return self.facts.get('impact')
    
    @numeric_rule_variable
    def age_days(self):
        """Get age in days from facts."""
        return self.facts.get('age_days', 0)
    
    @string_rule_variable
    def priority(self):
        """Get priority from facts."""
        return self.facts.get('priority')

class ContextActions(BaseActions):
    """Actions for context selection rules."""
    
    def __init__(self):
        self.score = 0
    
    @rule_action(params={"points": FIELD_NUMERIC})
    def add_score(self, points):
        """Add points to the score."""
        self.score += points
    
    def get_score(self) -> int:
        """Get the current score."""
        return self.score

    def get_results(self) -> Dict:
        """Get the results of rule execution."""
        return {
            "success": True,
            "score": self.score
        }

class ContextSelection:
    def __init__(self, rules):
        self.rules = rules

    def run(self, facts: Dict) -> Dict:
        """Run rules engine with facts."""
        variables = ContextVariables(facts)
        actions = ContextActions()
        run_all(rule_list=self.rules,
               variables=variables,
               actions=actions,
               stop_on_first_trigger=False)
        return actions.get_results() 