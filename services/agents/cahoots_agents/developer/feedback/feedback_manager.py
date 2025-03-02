"""Feedback management functionality for the developer agent."""

import json
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Tuple


class FeedbackType(Enum):
    """Types of feedback that can be provided."""

    REVIEW = "review"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    SECURITY = "security"


class FeedbackPriority(Enum):
    """Priority levels for feedback."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FeedbackStatus(Enum):
    """Status of feedback processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    INTEGRATED = "integrated"
    REJECTED = "rejected"
    REQUIRES_CLARIFICATION = "requires_clarification"


class FeedbackManager:
    """Handles feedback integration and management."""

    def __init__(self, agent):
        """Initialize the feedback manager.

        Args:
            agent: The developer agent instance
        """
        self.agent = agent
        self.logger = logging.getLogger(__name__)
        self.feedback_history: List[Dict[str, Any]] = []

    async def process_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Process feedback and determine required actions.

        Args:
            feedback: Dictionary containing feedback details including:
                     - task_id: ID of the related task
                     - feedback: The actual feedback content
                     - type: Type of feedback (review/implementation/etc)
                     - metadata: Additional context (optional)

        Returns:
            Dictionary containing processing results

        Raises:
            ValueError: If feedback format is invalid
        """
        # Validate required fields
        required_fields = ["task_id", "feedback", "type"]
        if not all(field in feedback for field in required_fields):
            raise ValueError("Invalid feedback format")

        prompt = f"""
        Task ID: {feedback['task_id']}
        Feedback Type: {feedback['type']}
        Feedback Content: {feedback['feedback']}
        Metadata: {feedback.get('metadata', {})}
        
        Analyze this feedback and determine required actions. Return as JSON:
        {{
            "status": "success|failure",
            "priority": "high|medium|low",
            "changes": [
                {{
                    "file": "file path",
                    "line": line_number,
                    "change": "suggested change"
                }}
            ],
            "suggestions": [
                "improvement suggestion 1",
                "improvement suggestion 2"
            ]
        }}
        """

        try:
            response = await self.agent.generate_response(prompt)
            result = json.loads(response)

            # Validate priority
            priority = result.get("priority", "medium").lower()
            if priority not in [p.value for p in FeedbackPriority]:
                priority = "medium"  # Default to medium if invalid

            # Store feedback in history
            self.integrate_feedback(
                {
                    **feedback,
                    "status": result.get("status", "pending"),
                    "priority": priority,
                    "timestamp": time.time(),
                }
            )

            result["priority"] = priority  # Ensure consistent priority in response
            return result

        except json.JSONDecodeError:
            raise ValueError("Failed to parse feedback response")
        except Exception as e:
            self.logger.error(f"Error processing feedback: {str(e)}")
            raise

    def integrate_feedback(self, feedback: Dict[str, Any]) -> None:
        """Integrate feedback into the agent's knowledge base.

        Args:
            feedback: Dictionary containing feedback details including:
                     - type (review/implementation)
                     - content (the actual feedback)
                     - context (code or PR context)
                     - outcome (success/failure)
                     - timestamp (optional)
        """
        # Preserve the existing timestamp or use current time as fallback
        feedback_copy = feedback.copy()
        if "timestamp" not in feedback_copy:
            feedback_copy["timestamp"] = time.time()
        self.feedback_history.append(feedback_copy)

    def get_relevant_feedback(self, context: str) -> List[Dict[str, Any]]:
        """Retrieve relevant feedback based on current context.

        Args:
            context: The current development context (e.g., task description, code)

        Returns:
            List[Dict[str, Any]]: List of relevant feedback entries
        """
        # Generate embeddings for context and feedback entries
        context_embedding = self.agent.generate_embedding(context)

        # Calculate similarity scores for all feedback
        scored_feedback: List[Tuple[float, Dict[str, Any]]] = []
        for entry in self.feedback_history:
            entry_embedding = self.agent.generate_embedding(entry.get("content", ""))
            similarity = self._calculate_similarity(context_embedding, entry_embedding)
            self.logger.debug(f"Similarity with entry '{entry.get('content', '')}': {similarity}")

            if similarity > 0.8:  # Standard threshold for cosine similarity
                scored_feedback.append((similarity, entry))

        # Sort by timestamp (descending)
        return [
            entry
            for _, entry in sorted(
                scored_feedback, key=lambda x: x[1].get("timestamp", 0), reverse=True
            )
        ][:5]

    def format_feedback_for_prompt(self, feedback: List[Dict[str, Any]]) -> str:
        """Format feedback history for inclusion in the prompt.

        Args:
            feedback: List of feedback entries to format

        Returns:
            str: Formatted feedback string
        """
        if not feedback:
            return "No relevant previous feedback available."

        formatted = []
        for entry in feedback:
            if entry["outcome"] == "success":
                formatted.append(
                    f"Previous Success Pattern:\n{entry.get('code', 'No code available')}"
                )
            else:
                formatted.append(f"Previous Issues to Avoid:\n{entry['content']}")

        return "\n\n".join(formatted)

    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Cosine similarity score
        """
        # Simple dot product for now - could be replaced with more sophisticated similarity
        return sum(a * b for a, b in zip(embedding1, embedding2))
