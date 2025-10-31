"""Feature Overlap Detector

Detects if requested features already exist in the linked repository.
Only checks for features explicitly mentioned in the user's request.
"""

from typing import Dict, Any, List, Optional
from app.analyzer.llm_client import LLMClient


class FeatureOverlapDetector:
    """Detects overlap between requested features and existing repository capabilities."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the feature overlap detector.

        Args:
            llm_client: LLM client for analysis
        """
        self.llm = llm_client

    async def detect_existing_features(
        self,
        user_prompt: str,
        repo_summary: str,
        file_summaries: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analyze if requested features already exist in the repository.

        Args:
            user_prompt: User's task description
            repo_summary: Summary of the repository
            file_summaries: Summaries of relevant files

        Returns:
            Dictionary with:
            - requested_features: List of features user is asking for
            - existing_features: Features that already exist
            - missing_features: Features that need to be implemented
            - overlap_details: Details about what exists and where
        """
        print(f"[FeatureOverlapDetector] Analyzing feature overlap...")

        # Build context from file summaries
        files_context = ""
        if file_summaries:
            files_context = "\n\nADDITIONAL FILE CONTEXT:\n"
            for path, summary in file_summaries.items():
                files_context += f"\n{path}:\n{summary}\n"

        prompt = f"""Analyze if the requested features already exist in this repository.

USER REQUEST:
{user_prompt}

REPOSITORY OVERVIEW:
{repo_summary}
{files_context}

Task:
1. Extract the specific features the user is requesting (e.g., "user authentication", "email password login", "OAuth", "password reset", etc.)
2. For each requested feature, determine if it already exists in the repository
3. Provide evidence (file paths, implementation details) for existing features

Return JSON with this structure:
{{
  "requested_features": [
    {{
      "name": "Feature name",
      "description": "What the feature does",
      "exists": true/false,
      "evidence": "Where it exists (file paths, implementation details) OR null if doesn't exist",
      "completeness": "complete/partial/missing",
      "notes": "Additional context about the existing implementation"
    }}
  ],
  "summary": {{
    "total_requested": 0,
    "already_exist": 0,
    "need_implementation": 0,
    "overlap_percentage": 0.0
  }}
}}

Be specific about what exists. For example:
- "User authentication with email+password" might exist in app/routes/auth.py
- "Google OAuth" might exist in app/integrations/google.py
- "Password reset flow" might be missing even if auth exists

Return ONLY valid JSON, no explanation.
"""

        response = await self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.2
        )

        if isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"]
        else:
            content = str(response)

        result = self.llm._parse_json(content)

        print(f"[FeatureOverlapDetector] ✅ Analysis complete:")
        print(f"  - Requested features: {result['summary']['total_requested']}")
        print(f"  - Already exist: {result['summary']['already_exist']}")
        print(f"  - Need implementation: {result['summary']['need_implementation']}")
        print(f"  - Overlap: {result['summary']['overlap_percentage']:.1f}%")

        return result

    async def filter_redundant_tasks(
        self,
        tasks: List[Dict[str, Any]],
        existing_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filter out tasks that implement already-existing features.

        Args:
            tasks: List of generated tasks
            existing_features: Output from detect_existing_features

        Returns:
            Dictionary with:
            - filtered_tasks: Tasks that should be kept
            - removed_tasks: Tasks that were filtered out
            - removal_reasons: Reasons for each removal
        """
        if not existing_features.get("requested_features"):
            # No overlap detected, keep all tasks
            return {
                "filtered_tasks": tasks,
                "removed_tasks": [],
                "removal_reasons": {}
            }

        # Build list of existing feature names for quick lookup
        existing_feature_names = [
            f["name"].lower()
            for f in existing_features["requested_features"]
            if f["exists"] and f["completeness"] in ["complete", "partial"]
        ]

        if not existing_feature_names:
            # Nothing exists, keep all tasks
            return {
                "filtered_tasks": tasks,
                "removed_tasks": [],
                "removal_reasons": {}
            }

        print(f"[FeatureOverlapDetector] Filtering tasks against existing features...")

        # Ask LLM to match tasks to existing features
        tasks_text = "\n".join([
            f"{i+1}. {task.get('description', '')}"
            for i, task in enumerate(tasks)
        ])

        existing_text = "\n".join([
            f"- {f['name']}: {f['evidence']}"
            for f in existing_features["requested_features"]
            if f["exists"]
        ])

        prompt = f"""Identify which tasks are redundant because the features already exist.

EXISTING FEATURES IN REPOSITORY:
{existing_text}

PROPOSED TASKS:
{tasks_text}

For each task, determine if it's redundant (implementing something that already exists).

Return JSON:
{{
  "task_analysis": [
    {{
      "task_index": 0,  // 0-based index
      "is_redundant": true/false,
      "reason": "Why it's redundant OR why it's still needed",
      "matching_feature": "Which existing feature it overlaps with OR null"
    }}
  ]
}}

IMPORTANT:
- Only mark as redundant if the feature is COMPLETE
- If a task extends/modifies an existing feature, it's NOT redundant
- If a task adds a missing piece, it's NOT redundant

Return ONLY valid JSON, no explanation.
"""

        response = await self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.1
        )

        if isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"]
        else:
            content = str(response)

        analysis = self.llm._parse_json(content)

        # Filter tasks based on analysis
        filtered_tasks = []
        removed_tasks = []
        removal_reasons = {}

        for task_info in analysis.get("task_analysis", []):
            task_index = task_info["task_index"]
            if task_index < len(tasks):
                task = tasks[task_index]
                if task_info["is_redundant"]:
                    removed_tasks.append(task)
                    removal_reasons[task.get("description", "")] = {
                        "reason": task_info["reason"],
                        "existing_feature": task_info["matching_feature"]
                    }
                    print(f"  ✗ Removed: {task.get('description', '')[:80]}")
                    print(f"    Reason: {task_info['reason']}")
                else:
                    filtered_tasks.append(task)

        print(f"[FeatureOverlapDetector] ✅ Filtered {len(removed_tasks)} redundant tasks")
        print(f"  - Kept: {len(filtered_tasks)} tasks")
        print(f"  - Removed: {len(removed_tasks)} tasks")

        return {
            "filtered_tasks": filtered_tasks,
            "removed_tasks": removed_tasks,
            "removal_reasons": removal_reasons
        }
