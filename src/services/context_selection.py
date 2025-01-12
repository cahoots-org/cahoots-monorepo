"""Context selection service for LLM request enrichment."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from src.core.dependencies import BaseDeps
from src.services.context_service import ContextEventService

class ContextSelectionService:
    def __init__(self, deps: BaseDeps):
        """Initialize context selection service.
        
        Args:
            deps: Base dependencies including database and context service
        """
        self.db = deps.db
        self.context_service = deps.context_service
        
    async def get_llm_context(
        self,
        project_id: UUID,
        request_type: str,
        relevant_files: Optional[List[str]] = None,
        max_context_items: int = 50
    ) -> Dict:
        """
        Get relevant context for an LLM request.
        
        Args:
            project_id: Project ID
            request_type: Type of LLM request (e.g., 'code_generation', 'code_review', 'architectural_decision')
            relevant_files: List of files relevant to the request
            max_context_items: Maximum number of context items to include
            
        Returns:
            Dict containing selected context items organized by category
        """
        # Get full project context
        full_context = await self.context_service.get_context(project_id)
        
        # Initialize selected context
        selected_context = {
            "code_changes": [],
            "architectural_decisions": [],
            "standards": {},
            "discussions": [],
            "patterns": [],
            "requirements": {}
        }
        
        # Select recent code changes for relevant files
        if "code_changes" in full_context:
            changes = self._filter_code_changes(
                full_context["code_changes"],
                relevant_files,
                max_items=20
            )
            selected_context["code_changes"] = changes
            
        # Include all architectural decisions as they're usually important
        if "architectural_decisions" in full_context:
            selected_context["architectural_decisions"] = full_context["architectural_decisions"]
            
        # Include relevant standards
        if "standards" in full_context:
            selected_context["standards"] = self._filter_standards(
                full_context["standards"],
                request_type
            )
            
        # Include relevant discussions
        if "discussions" in full_context:
            discussions = self._filter_discussions(
                full_context["discussions"],
                request_type,
                relevant_files,
                max_items=10
            )
            selected_context["discussions"] = discussions
            
        # Include project patterns
        if "patterns" in full_context:
            selected_context["patterns"] = self._filter_patterns(
                full_context["patterns"],
                request_type
            )
            
        # Include relevant requirements
        if "requirements" in full_context:
            selected_context["requirements"] = self._filter_requirements(
                full_context["requirements"],
                request_type,
                relevant_files
            )
            
        return selected_context
    
    def _filter_code_changes(
        self,
        changes: List[Dict],
        relevant_files: Optional[List[str]],
        max_items: int = 20,
        max_age_days: int = 30
    ) -> List[Dict]:
        """Filter code changes by relevance and recency."""
        if not changes:
            return []
            
        # Filter by file relevance if files specified
        if relevant_files:
            changes = [
                change for change in changes
                if any(file in change.get("files", []) for file in relevant_files)
            ]
            
        # Filter by age
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        changes = [
            change for change in changes
            if datetime.fromisoformat(change["timestamp"]) > cutoff_date
        ]
        
        # Sort by timestamp and take most recent
        changes.sort(key=lambda x: x["timestamp"], reverse=True)
        return changes[:max_items]
    
    def _filter_standards(self, standards: Dict, request_type: str) -> Dict:
        """Filter standards by request type."""
        relevant_standards = {}
        
        # Always include global standards
        if "global" in standards:
            relevant_standards["global"] = standards["global"]
            
        # Include standards specific to request type
        if request_type in standards:
            relevant_standards[request_type] = standards[request_type]
            
        # Include language/framework specific standards if relevant
        if request_type == "code_generation":
            for key in ["python", "typescript", "testing", "security"]:
                if key in standards:
                    relevant_standards[key] = standards[key]
                    
        return relevant_standards
    
    def _filter_discussions(
        self,
        discussions: List[Dict],
        request_type: str,
        relevant_files: Optional[List[str]],
        max_items: int = 10
    ) -> List[Dict]:
        """Filter discussions by relevance."""
        if not discussions:
            return []
            
        # Score discussions by relevance
        scored_discussions = []
        for discussion in discussions:
            score = 0
            
            # Score by type relevance
            if discussion.get("type") == request_type:
                score += 5
                
            # Score by file relevance
            if relevant_files and any(
                file in discussion.get("related_files", [])
                for file in relevant_files
            ):
                score += 3
                
            # Score by recency
            days_old = (
                datetime.utcnow() -
                datetime.fromisoformat(discussion["timestamp"])
            ).days
            score += max(0, 10 - days_old/3)  # Decay score with age
            
            scored_discussions.append((score, discussion))
            
        # Sort by score and take top items
        scored_discussions.sort(reverse=True)
        return [d[1] for d in scored_discussions[:max_items]]
    
    def _filter_patterns(self, patterns: List[Dict], request_type: str) -> List[Dict]:
        """Filter patterns by request type."""
        if not patterns:
            return []
            
        return [
            pattern for pattern in patterns
            if request_type in pattern.get("applicable_to", [])
        ]
    
    def _filter_requirements(
        self,
        requirements: Dict,
        request_type: str,
        relevant_files: Optional[List[str]]
    ) -> Dict:
        """Filter requirements by relevance."""
        relevant_reqs = {}
        
        # Include performance requirements
        if "performance" in requirements:
            relevant_reqs["performance"] = requirements["performance"]
            
        # Include quality requirements
        if "quality" in requirements:
            relevant_reqs["quality"] = requirements["quality"]
            
        # Include security requirements for security-sensitive operations
        if "security" in requirements and (
            request_type in ["security_review", "code_generation"]
            or any(
                "security" in req.get("tags", [])
                for req in requirements.get("functional", [])
            )
        ):
            relevant_reqs["security"] = requirements["security"]
            
        # Include functional requirements if files are specified
        if relevant_files and "functional" in requirements:
            relevant_reqs["functional"] = [
                req for req in requirements["functional"]
                if any(
                    file in req.get("related_files", [])
                    for file in relevant_files
                )
            ]
            
        return relevant_reqs 