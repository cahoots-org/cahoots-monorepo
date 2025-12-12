"""Epic analyzer for generating and managing epics from root tasks."""

from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime, timezone

from app.models import Epic, EpicStatus, EpicGeneration, UserStory
from .llm_client import LLMClient


# Clarifying question schema
class ClarifyingQuestion:
    """A clarifying question to help refine project understanding."""
    def __init__(
        self,
        id: str,
        question: str,
        question_type: str = "short_text",
        options: List[str] = None,
        category: str = "general",
        importance: str = "medium"
    ):
        self.id = id
        self.question = question
        self.type = question_type  # multiple_choice, short_text, yes_no
        self.options = options or []
        self.category = category  # scale, users, integrations, constraints, tech
        self.importance = importance  # high, medium, low

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "type": self.type,
            "options": self.options,
            "category": self.category,
            "importance": self.importance
        }


class EpicAnalyzer:
    """Analyzes root tasks and generates comprehensive epics."""

    def __init__(self, llm_client: LLMClient):
        """Initialize the epic analyzer.

        Args:
            llm_client: LLM client for making API calls
        """
        self.llm = llm_client

    async def generate_epics(
        self,
        root_description: str,
        root_task_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[EpicGeneration, List[ClarifyingQuestion]]:
        """Generate comprehensive epics from a root task description.

        This should identify ALL major functional areas upfront to ensure
        complete coverage of the system. Also generates clarifying questions
        to help refine understanding.

        Args:
            root_description: The root task description
            root_task_id: ID of the root task
            context: Optional context (tech stack, preferences, etc.)

        Returns:
            Tuple of (EpicGeneration with all epics, List of clarifying questions)
        """
        system_prompt = self._build_epic_generation_prompt(context)
        user_prompt = f"""Generate the major functional areas (Epics) for this system, AND generate clarifying questions to better understand the requirements.

Task: "{root_description}"

Guidelines for Epics:
- Apply the independence test: Could these be built as separate products?
- Group features that share data, users, or workflows into the same epic
- Only split if teams could work completely independently
- Focus on what was explicitly requested
- Keep scope appropriate to the complexity of the request

For each epic, provide:
- title: Short, descriptive title
- description: Clear description of what this epic covers
- scope_keywords: 5-10 keywords that help classify future stories to this epic
- priority: 1-5 (1=critical for MVP, 5=nice to have)
- estimated_complexity: low/medium/high

Guidelines for Clarifying Questions:
- Generate 10-15 questions that would help refine the project scope
- Order by importance (most important first)
- Focus on ambiguities, scale, user types, integrations, and constraints
- Prefer multiple-choice questions (faster to answer)
- Questions should be quick to answer (not essays)

For each clarifying_question, provide:
- id: Q-001, Q-002, etc.
- question: The question text
- type: "multiple_choice", "yes_no", or "short_text"
- options: Array of options (for multiple_choice only, 2-5 options)
- category: "scale", "users", "integrations", "constraints", "tech", or "features"
- importance: "high", "medium", or "low"

Also provide:
- coverage_analysis: Brief analysis confirming all aspects are covered
- generation_reasoning: Why you broke it down this way
- suggested_priority_order: List of epic titles in implementation order

Return as JSON with keys: epics, clarifying_questions, coverage_analysis, generation_reasoning, suggested_priority_order"""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=12000  # Increased for epics + questions
            )

            # Debug: Log response to understand what we got
            print(f"[EpicAnalyzer] LLM response keys: {list(response.keys())}")
            print(f"[EpicAnalyzer] Epics count in response: {len(response.get('epics', []))}")
            print(f"[EpicAnalyzer] Questions count in response: {len(response.get('clarifying_questions', []))}")

            # Parse epics from response
            epics = []
            epic_data_list = response.get("epics", [])

            # Validate that we actually got epics - if the response is empty, raise an error
            if not epic_data_list:
                error_msg = f"LLM returned empty epics list. Response: {response}"
                print(f"[EpicAnalyzer] ERROR: {error_msg}")
                raise ValueError(error_msg)

            for i, epic_data in enumerate(epic_data_list):
                epic = Epic(
                    id=f"EP-{i+1}",
                    title=epic_data.get("title", f"Epic {i+1}"),
                    description=epic_data.get("description", ""),
                    scope_keywords=epic_data.get("scope_keywords", []),
                    priority=epic_data.get("priority", 3),
                    root_task_id=root_task_id,
                    status=EpicStatus.ACTIVE
                )
                epics.append(epic)

            # Parse clarifying questions from response
            questions = []
            questions_data = response.get("clarifying_questions", [])
            for q_data in questions_data:
                question = ClarifyingQuestion(
                    id=q_data.get("id", f"Q-{len(questions)+1:03d}"),
                    question=q_data.get("question", ""),
                    question_type=q_data.get("type", "short_text"),
                    options=q_data.get("options", []),
                    category=q_data.get("category", "general"),
                    importance=q_data.get("importance", "medium")
                )
                questions.append(question)

            epic_generation = EpicGeneration(
                epics=epics,
                coverage_analysis=response.get("coverage_analysis", {}),
                generation_reasoning=response.get("generation_reasoning", ""),
                suggested_priority_order=response.get("suggested_priority_order", [])
            )

            return epic_generation, questions

        except Exception as e:
            print(f"Error generating epics: {e}")
            # Fallback to a single epic if generation fails
            fallback_epic = Epic(
                id="EP-1",
                title="Main Functionality",
                description=root_description,
                scope_keywords=["main", "core", "primary"],
                priority=1,
                root_task_id=root_task_id
            )
            return EpicGeneration(
                epics=[fallback_epic],
                generation_reasoning=f"Fallback generation due to error: {str(e)}"
            ), []  # Empty questions list on fallback

    async def classify_to_epic(
        self,
        task_description: str,
        epics: List[Epic],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Epic], float]:
        """Classify a task/story to the most appropriate epic.

        Uses both keyword matching and semantic similarity to determine
        the best epic for a given task.

        Args:
            task_description: Description of the task/story to classify
            epics: List of available epics
            context: Optional context

        Returns:
            Tuple of (best_epic, confidence_score)
        """
        if not epics:
            return None, 0.0

        # First try keyword-based classification
        keyword_scores = {}
        for epic in epics:
            score = self._calculate_keyword_score(task_description, epic)
            keyword_scores[epic.id] = score

        # Get the best keyword match
        best_keyword_epic_id = max(keyword_scores, key=keyword_scores.get)
        best_keyword_score = keyword_scores[best_keyword_epic_id]

        # If keyword score is very high, use it
        if best_keyword_score > 0.7:
            best_epic = next(e for e in epics if e.id == best_keyword_epic_id)
            return best_epic, best_keyword_score

        # Otherwise, use LLM for semantic classification
        epic_summaries = [
            f"{epic.id}: {epic.title} - {epic.description[:100]}"
            for epic in epics
        ]

        system_prompt = """You are classifying a task to the most appropriate epic.
Consider the semantic meaning and functional area of the task."""

        user_prompt = f"""Which epic does this task belong to?

Task: "{task_description}"

Available Epics:
{chr(10).join(epic_summaries)}

Return JSON with:
- epic_id: The ID of the best matching epic
- confidence: 0.0-1.0 confidence score
- reasoning: Brief explanation"""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.1,
                max_tokens=500
            )

            epic_id = response.get("epic_id")
            confidence = response.get("confidence", 0.5)

            # Find the epic
            best_epic = next((e for e in epics if e.id == epic_id), None)

            # Combine keyword and semantic scores
            if best_epic:
                combined_score = (keyword_scores.get(epic_id, 0) * 0.3) + (confidence * 0.7)
                return best_epic, combined_score

        except Exception as e:
            print(f"Error in semantic classification: {e}")

        # Fallback to best keyword match
        best_epic = next(e for e in epics if e.id == best_keyword_epic_id)
        return best_epic, best_keyword_score

    async def check_epic_coverage_gaps(
        self,
        task_description: str,
        epics: List[Epic],
        threshold: float = 0.5
    ) -> bool:
        """Check if a task represents a gap in epic coverage.

        A gap exists if the task doesn't fit well into any existing epic.

        Args:
            task_description: Task to check
            epics: Existing epics
            threshold: Minimum score to consider covered

        Returns:
            True if this represents a coverage gap
        """
        if not epics:
            return True

        best_epic, score = await self.classify_to_epic(task_description, epics)
        return score < threshold

    async def generate_epic_for_gap(
        self,
        task_description: str,
        root_task_id: str,
        existing_epics: List[Epic],
        context: Optional[Dict[str, Any]] = None
    ) -> Epic:
        """Generate a new epic for functionality not covered by existing epics.

        This is triggered when a complex task doesn't fit into any existing epic.

        Args:
            task_description: Task that triggered the gap
            root_task_id: Root task ID
            existing_epics: List of existing epics
            context: Optional context

        Returns:
            New epic to cover the gap
        """
        existing_titles = [epic.title for epic in existing_epics]

        system_prompt = """You are identifying a new major functional area (Epic)
that was missed in initial analysis."""

        user_prompt = f"""A complex task was found that doesn't fit existing epics.
Generate a new epic to cover this functionality.

Task triggering gap: "{task_description}"

Existing epics: {', '.join(existing_titles)}

Provide:
- title: Short, descriptive title for the new functional area
- description: What this epic covers
- scope_keywords: 5-10 keywords for classification
- priority: 1-5
- reasoning: Why this is a distinct functional area

Return as JSON."""

        try:
            response = await self.llm.generate_json(
                system_prompt,
                user_prompt,
                temperature=0.3,
                max_tokens=1000
            )

            new_epic_id = f"EP-{len(existing_epics) + 1}"
            return Epic(
                id=new_epic_id,
                title=response.get("title", "Additional Functionality"),
                description=response.get("description", task_description),
                scope_keywords=response.get("scope_keywords", []),
                priority=response.get("priority", 3),
                root_task_id=root_task_id,
                status=EpicStatus.ACTIVE,
                metadata={"gap_triggered": True, "trigger_task": task_description}
            )

        except Exception as e:
            print(f"Error generating gap epic: {e}")
            # Fallback epic
            return Epic(
                id=f"EP-{len(existing_epics) + 1}",
                title="Additional Features",
                description=f"Epic for: {task_description}",
                scope_keywords=[],
                priority=3,
                root_task_id=root_task_id
            )

    def _calculate_keyword_score(self, description: str, epic: Epic) -> float:
        """Calculate keyword-based matching score.

        Args:
            description: Task description
            epic: Epic to match against

        Returns:
            Score from 0.0 to 1.0
        """
        if not epic.scope_keywords:
            return 0.0

        description_lower = description.lower()
        matches = sum(
            1 for keyword in epic.scope_keywords
            if keyword.lower() in description_lower
        )

        return min(matches / max(len(epic.scope_keywords), 1), 1.0)

    def _build_epic_generation_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build system prompt for epic generation.

        Args:
            context: Optional context dictionary

        Returns:
            System prompt string
        """
        base_prompt = """You are a product manager breaking down a request into epics.
Epics are major functional areas that group related user stories.

CORE PRINCIPLE: Break down the system by BUSINESS DOMAIN, not by technical layers or dependencies.
Different business concerns should be separate epics even if they share some data.

For any application, ask: "What are the distinct business capabilities?"
- User Management (registration, profiles, settings) → 1 epic
- Core Business Logic (what the app DOES) → 1-2 epics depending on complexity
- Payments/Financial (billing, credits, transactions) → 1 epic
- Trust & Safety (ratings, reviews, disputes, moderation) → 1 epic
- Notifications & Communication → 1 epic (if substantial)
- Admin/Operations → 1 epic (if admin features are extensive)

Scale by complexity:
- Simple feature/tool → 1-2 epics
- Medium app (blog, chat, simple marketplace) → 2-4 epics
- Complex platform (e-commerce, multi-sided marketplace, SaaS) → 4-6 epics
- Enterprise system → 6+ epics

IMPORTANT: For platforms with TWO-SIDED MARKETPLACES, ESCROW, or PAYMENT SYSTEMS:
These are complex systems that MUST have multiple epics. Break down by:
1. User Management (both user types)
2. Core Marketplace (listings, matching, discovery)
3. Transactions/Payments/Escrow
4. Fulfillment/Delivery/Sessions
5. Trust & Safety (ratings, disputes, verification)

Never create separate epics for:
- Technical layers (UI, backend, database) - these are NOT epics
- Implementation details (input handling, data storage)
- Different views of the same feature (e.g., list view vs detail view)"""

        if context:
            tech_stack = context.get("tech_stack", "")
            domain = context.get("domain", "")

            if tech_stack:
                base_prompt += f"\n\nTech Stack: {tech_stack}"
            if domain:
                base_prompt += f"\n\nDomain: {domain}"

        return base_prompt