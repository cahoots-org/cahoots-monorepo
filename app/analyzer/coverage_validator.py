"""Coverage validation for ensuring complete epic/story/task hierarchy."""

from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass

from app.models import Epic, UserStory, Task


@dataclass
class CoverageGap:
    """Represents a gap in coverage."""
    level: str  # "epic", "story", "task"
    parent_id: str
    description: str
    severity: str  # "critical", "major", "minor"
    suggested_action: str


@dataclass
class CoverageOverlap:
    """Represents an overlap between siblings."""
    level: str  # "epic", "story", "task"
    item1_id: str
    item2_id: str
    overlap_description: str
    severity: str  # "high", "medium", "low"


@dataclass
class CoverageReport:
    """Complete coverage validation report."""
    is_complete: bool
    coverage_score: float
    gaps: List[CoverageGap]
    overlaps: List[CoverageOverlap]
    statistics: Dict[str, Any]
    recommendations: List[str]


class CoverageValidator:
    """Validates coverage and detects gaps/overlaps in the hierarchy."""

    def __init__(self):
        """Initialize the coverage validator."""
        pass

    def validate_epic_coverage(
        self,
        root_task: Task,
        epics: List[Epic]
    ) -> Tuple[List[CoverageGap], float]:
        """Validate that epics completely cover the root task.

        Args:
            root_task: The root task
            epics: List of epics

        Returns:
            Tuple of (gaps, coverage_score)
        """
        gaps = []

        if not epics:
            gaps.append(CoverageGap(
                level="epic",
                parent_id=root_task.id,
                description="No epics defined",
                severity="critical",
                suggested_action="Generate comprehensive epics for the root task"
            ))
            return gaps, 0.0

        # Extract functional areas from root task
        root_aspects = self._extract_functional_aspects(root_task.description)

        # Collect what epics cover
        covered_aspects = set()
        for epic in epics:
            epic_aspects = self._extract_functional_aspects(
                f"{epic.title} {epic.description}"
            )
            covered_aspects.update(epic_aspects)

        # Find uncovered aspects
        uncovered = root_aspects - covered_aspects

        if uncovered:
            for aspect in uncovered:
                gaps.append(CoverageGap(
                    level="epic",
                    parent_id=root_task.id,
                    description=f"Functionality not covered: {aspect}",
                    severity="major" if len(uncovered) > 2 else "minor",
                    suggested_action=f"Create epic or expand existing epic to cover: {aspect}"
                ))

        coverage_score = len(covered_aspects) / max(len(root_aspects), 1)
        return gaps, coverage_score

    def validate_story_coverage(
        self,
        epic: Epic,
        stories: List[UserStory],
        child_tasks: List[Task]
    ) -> Tuple[List[CoverageGap], float]:
        """Validate that stories cover the epic and tasks are covered by stories.

        Args:
            epic: The parent epic
            stories: Stories in the epic
            child_tasks: Tasks that should be covered by stories

        Returns:
            Tuple of (gaps, coverage_score)
        """
        gaps = []

        if not stories:
            gaps.append(CoverageGap(
                level="story",
                parent_id=epic.id,
                description=f"No stories defined for epic: {epic.title}",
                severity="major",
                suggested_action="Generate initial stories for this epic"
            ))
            return gaps, 0.0 if child_tasks else 1.0

        # Check if tasks are covered by stories
        uncovered_tasks = []
        for task in child_tasks:
            if not task.story_ids:
                uncovered_tasks.append(task)

        if uncovered_tasks:
            for task in uncovered_tasks[:3]:  # Limit to first 3 for brevity
                gaps.append(CoverageGap(
                    level="story",
                    parent_id=epic.id,
                    description=f"Task not covered by stories: {task.description[:50]}",
                    severity="major",
                    suggested_action=f"Generate story for task or assign to existing story"
                ))

        # Calculate coverage
        covered_count = len(child_tasks) - len(uncovered_tasks)
        coverage_score = covered_count / max(len(child_tasks), 1) if child_tasks else 1.0

        return gaps, coverage_score

    def detect_epic_overlaps(
        self,
        epics: List[Epic]
    ) -> List[CoverageOverlap]:
        """Detect overlaps between epics.

        Args:
            epics: List of epics to check

        Returns:
            List of detected overlaps
        """
        overlaps = []

        for i, epic1 in enumerate(epics):
            for epic2 in epics[i+1:]:
                overlap_score = self._calculate_overlap_score(
                    epic1.scope_keywords,
                    epic2.scope_keywords
                )

                if overlap_score > 0.3:  # Significant overlap threshold
                    severity = "high" if overlap_score > 0.6 else "medium"
                    overlaps.append(CoverageOverlap(
                        level="epic",
                        item1_id=epic1.id,
                        item2_id=epic2.id,
                        overlap_description=f"{epic1.title} and {epic2.title} have overlapping scope",
                        severity=severity
                    ))

        return overlaps

    def detect_story_overlaps(
        self,
        stories: List[UserStory]
    ) -> List[CoverageOverlap]:
        """Detect overlaps between stories within an epic.

        Args:
            stories: List of stories to check

        Returns:
            List of detected overlaps
        """
        overlaps = []

        for i, story1 in enumerate(stories):
            for story2 in stories[i+1:]:
                # Check if stories are in the same epic
                if story1.epic_id != story2.epic_id:
                    continue

                # Check for similar actions
                if self._are_stories_similar(story1, story2):
                    overlaps.append(CoverageOverlap(
                        level="story",
                        item1_id=story1.id,
                        item2_id=story2.id,
                        overlap_description=f"Similar user stories: both handle {story1.action[:30]}",
                        severity="medium"
                    ))

        return overlaps

    def generate_coverage_report(
        self,
        root_task: Task,
        epics: List[Epic],
        all_stories: List[UserStory],
        all_tasks: List[Task]
    ) -> CoverageReport:
        """Generate a comprehensive coverage report.

        Args:
            root_task: The root task
            epics: All epics
            all_stories: All user stories
            all_tasks: All tasks in the tree

        Returns:
            Complete coverage report
        """
        gaps = []
        overlaps = []

        # Check epic coverage
        epic_gaps, epic_coverage = self.validate_epic_coverage(root_task, epics)
        gaps.extend(epic_gaps)

        # Check epic overlaps
        epic_overlaps = self.detect_epic_overlaps(epics)
        overlaps.extend(epic_overlaps)

        # Check story coverage per epic
        story_coverage_scores = []
        for epic in epics:
            epic_stories = [s for s in all_stories if s.epic_id == epic.id]
            epic_tasks = [t for t in all_tasks if epic.id in t.epic_ids]

            story_gaps, story_coverage = self.validate_story_coverage(
                epic, epic_stories, epic_tasks
            )
            gaps.extend(story_gaps)
            story_coverage_scores.append(story_coverage)

        # Check story overlaps
        story_overlaps = self.detect_story_overlaps(all_stories)
        overlaps.extend(story_overlaps)

        # Calculate overall coverage score
        avg_story_coverage = sum(story_coverage_scores) / max(len(story_coverage_scores), 1)
        overall_coverage = (epic_coverage * 0.4) + (avg_story_coverage * 0.6)

        # Generate statistics
        statistics = {
            "total_epics": len(epics),
            "total_stories": len(all_stories),
            "total_tasks": len(all_tasks),
            "epic_coverage": epic_coverage,
            "avg_story_coverage": avg_story_coverage,
            "gaps_count": len(gaps),
            "overlaps_count": len(overlaps),
            "uncovered_tasks": len([t for t in all_tasks if not t.story_ids]),
            "stories_per_epic": len(all_stories) / max(len(epics), 1)
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(gaps, overlaps, statistics)

        return CoverageReport(
            is_complete=len(gaps) == 0 and len(overlaps) == 0,
            coverage_score=overall_coverage,
            gaps=gaps,
            overlaps=overlaps,
            statistics=statistics,
            recommendations=recommendations
        )

    def _extract_functional_aspects(self, description: str) -> Set[str]:
        """Extract functional aspects from a description.

        Args:
            description: Text to analyze

        Returns:
            Set of functional aspects
        """
        # Simple keyword extraction - could be enhanced with NLP
        keywords = set()

        # Common functional areas
        functional_keywords = [
            "authentication", "auth", "login", "user", "admin",
            "payment", "billing", "checkout", "cart", "order",
            "product", "catalog", "inventory", "stock",
            "report", "analytics", "dashboard", "monitoring",
            "api", "integration", "webhook", "notification",
            "search", "filter", "sort", "pagination",
            "upload", "download", "file", "media",
            "settings", "config", "preferences", "profile"
        ]

        description_lower = description.lower()
        for keyword in functional_keywords:
            if keyword in description_lower:
                keywords.add(keyword)

        return keywords

    def _calculate_overlap_score(
        self,
        keywords1: List[str],
        keywords2: List[str]
    ) -> float:
        """Calculate overlap score between two keyword sets.

        Args:
            keywords1: First set of keywords
            keywords2: Second set of keywords

        Returns:
            Overlap score from 0.0 to 1.0
        """
        if not keywords1 or not keywords2:
            return 0.0

        set1 = set(k.lower() for k in keywords1)
        set2 = set(k.lower() for k in keywords2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        smaller_set_size = min(len(set1), len(set2))

        return intersection / smaller_set_size

    def _are_stories_similar(
        self,
        story1: UserStory,
        story2: UserStory,
        threshold: float = 0.7
    ) -> bool:
        """Check if two stories are too similar.

        Args:
            story1: First story
            story2: Second story
            threshold: Similarity threshold

        Returns:
            True if stories are too similar
        """
        # Check actor similarity
        if story1.actor.lower() == story2.actor.lower():
            # Check action similarity
            action1_words = set(story1.action.lower().split())
            action2_words = set(story2.action.lower().split())

            if not action1_words or not action2_words:
                return False

            overlap = len(action1_words & action2_words)
            similarity = overlap / min(len(action1_words), len(action2_words))

            return similarity >= threshold

        return False

    def _generate_recommendations(
        self,
        gaps: List[CoverageGap],
        overlaps: List[CoverageOverlap],
        statistics: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations.

        Args:
            gaps: Detected gaps
            overlaps: Detected overlaps
            statistics: Coverage statistics

        Returns:
            List of recommendations
        """
        recommendations = []

        # Gap recommendations
        critical_gaps = [g for g in gaps if g.severity == "critical"]
        if critical_gaps:
            recommendations.append(
                f"CRITICAL: {len(critical_gaps)} critical gaps found. "
                "Generate epics/stories immediately to ensure complete coverage."
            )

        # Overlap recommendations
        high_overlaps = [o for o in overlaps if o.severity == "high"]
        if high_overlaps:
            recommendations.append(
                f"HIGH PRIORITY: {len(high_overlaps)} significant overlaps found. "
                "Review and consolidate overlapping epics/stories."
            )

        # Coverage recommendations
        if statistics["epic_coverage"] < 0.8:
            recommendations.append(
                "Epic coverage is below 80%. Consider adding epics for uncovered functionality."
            )

        if statistics["avg_story_coverage"] < 0.7:
            recommendations.append(
                "Story coverage is low. Generate stories for gaps or review task assignments."
            )

        # Balance recommendations
        if statistics["stories_per_epic"] < 2:
            recommendations.append(
                "Some epics have very few stories. Consider decomposing epics further."
            )
        elif statistics["stories_per_epic"] > 10:
            recommendations.append(
                "Some epics have many stories. Consider splitting large epics."
            )

        if not recommendations:
            recommendations.append("Coverage looks good! All major areas are covered.")

        return recommendations