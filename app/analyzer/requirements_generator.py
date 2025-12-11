"""Requirements Generator

Generates functional and non-functional requirements from project analysis.
Derives requirements from user stories and their acceptance criteria for completeness.
"""

from typing import Dict, Any, List
import json




def _build_story_context(stories: List[Dict], max_stories: int = 60) -> str:
    """Build comprehensive story context including acceptance criteria."""
    story_lines = []

    for s in stories[:max_stories]:
        actor = s.get('actor', 'User')
        action = s.get('action', 'do something')
        benefit = s.get('benefit', '')
        epic_id = s.get('epic_id', '')

        # Build story line
        story_line = f"- [{epic_id}] As a {actor}, {action}"
        if benefit:
            story_line += f" so that {benefit}"

        # Include acceptance criteria (crucial for deriving requirements)
        criteria = s.get('acceptance_criteria', [])
        if criteria and len(criteria) > 0:
            # Include first 3 acceptance criteria to keep context manageable
            ac_list = criteria[:3] if isinstance(criteria, list) else []
            if ac_list:
                criteria_str = "; ".join([
                    c if isinstance(c, str) else str(c)
                    for c in ac_list
                ])
                story_line += f"\n  Acceptance: {criteria_str[:200]}"

        story_lines.append(story_line)

    return "\n".join(story_lines)


async def generate_requirements(
    llm_client,
    description: str,
    epics: List[Dict[str, Any]],
    stories: List[Dict[str, Any]],
    tech_stack: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate functional and non-functional requirements.

    Args:
        llm_client: LLM client for generation
        description: Project description
        epics: List of epics
        stories: List of user stories
        tech_stack: Tech stack choices

    Returns:
        Dict with functional_requirements and non_functional_requirements lists
    """
    print(f"[RequirementsGenerator] Project has {len(stories)} stories, {len(epics)} epics")

    # Build comprehensive epic context
    epic_list = "\n".join([
        f"- {e.get('title') or e.get('name', 'Untitled')}: {e.get('description', '')[:150]}"
        for e in epics
    ])

    # Build story context WITH acceptance criteria
    story_context = _build_story_context(stories, max_stories=60)

    # Extract tech stack services for NFRs
    tech_info = f"Frontend: {tech_stack.get('frontend', 'N/A')}, Backend: {tech_stack.get('backend', 'N/A')}"
    services = tech_stack.get('services', {})
    if services:
        service_list = ", ".join([f"{k}: {v}" for k, v in services.items()])
        tech_info += f"\nServices: {service_list}"

    prompt = f"""Generate comprehensive requirements for this software project.

PROJECT: {description}

BUSINESS AREAS ({len(epics)} epics):
{epic_list or "Not specified"}

USER STORIES ({len(stories)} total - derive requirements from these):
{story_context or "Not specified"}

TECH STACK: {tech_info}

TASK: Generate COMPREHENSIVE requirements by analyzing ALL user stories and their acceptance criteria.

Return JSON with two arrays:
1. functional_requirements - What the system must DO (FR-001 format)
2. non_functional_requirements - How well it must perform (NFR-001 format)

Format:
{{
  "functional_requirements": [
    {{"id": "FR-001", "category": "User Management", "requirement": "System shall allow users to register with email verification", "priority": "Must Have", "source_story": "US-1"}},
    {{"id": "FR-002", "category": "User Management", "requirement": "System shall lock accounts after 5 consecutive failed login attempts", "priority": "Must Have", "source_story": "US-3"}}
  ],
  "non_functional_requirements": [
    {{"id": "NFR-001", "category": "Financial Security", "requirement": "System shall implement secure payment processing with encryption and audit logging", "priority": "Must Have"}},
    {{"id": "NFR-002", "category": "Rating Integrity", "requirement": "System shall prevent manipulation of ratings and reviews", "priority": "Must Have"}}
  ]
}}

RULES FOR FUNCTIONAL REQUIREMENTS:
- Transform each user story and its acceptance criteria into formal requirements
- Group by category using epic/domain names
- Include source_story reference for traceability
- Priority: "Must Have", "Should Have", or "Could Have"
- Use "shall" language
- Be specific and measurable where appropriate

RULES FOR NON-FUNCTIONAL REQUIREMENTS:
- ONLY include NFRs that are RELEVANT to this specific project
- Derive from actual features in the stories, NOT generic standards
- Examples of context-specific NFRs:
  * Payments → Financial Security
  * User data → Data Protection
  * Messaging → Delivery Reliability
  * Ratings → Integrity Protection
  * Search → Performance targets
- Do NOT include boilerplate NFRs that don't apply

Return ONLY valid JSON."""

    # Calculate max_tokens based on expected output size
    # For comprehensive requirements, we need more tokens
    # Estimate: story count * 3 requirements avg * 100 tokens each
    estimated_reqs = len(stories) * 3
    max_tokens = min(32000, max(8000, estimated_reqs * 120))

    try:
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3
        )

        # Handle different response formats
        content = None
        if isinstance(response, dict):
            if "choices" in response:
                msg = response["choices"][0].get("message", {})
                if isinstance(msg, dict):
                    content = msg.get("content") or msg.get("reasoning") or ""
            elif "message" in response:
                content = response["message"].get("content", "")
            elif "content" in response:
                content = response["content"]
        elif isinstance(response, str):
            content = response

        if content:
            data = _parse_json_response(content)
            if data:
                functional = data.get("functional_requirements", [])
                non_functional = data.get("non_functional_requirements", [])

                print(f"[RequirementsGenerator] Generated {len(functional)} functional, {len(non_functional)} non-functional requirements")

                return {
                    "functional_requirements": functional,
                    "non_functional_requirements": non_functional
                }

    except Exception as e:
        print(f"[RequirementsGenerator] Error: {e}")

    # Fallback: generate basic requirements from stories
    print("[RequirementsGenerator] Using fallback generation")
    return _generate_fallback_requirements(stories, tech_stack)


def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response."""
    import re

    if not content:
        return None

    # Try direct parse
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # Try code block extraction
    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object
    start_idx = content.find('{')
    if start_idx != -1:
        brace_count = 0
        in_string = False
        escape = False

        for i in range(start_idx, len(content)):
            char = content[i]

            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char == '"' and not escape:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            return json.loads(content[start_idx:i+1])
                        except json.JSONDecodeError:
                            pass
                        break

    return None


def _generate_fallback_requirements(
    stories: List[Dict[str, Any]],
    tech_stack: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate comprehensive requirements from stories when LLM fails."""

    functional = []
    req_count = 0

    # Group stories by epic for better categorization
    stories_by_epic = {}
    for story in stories:
        epic_id = story.get('epic_id', 'Core')
        if epic_id not in stories_by_epic:
            stories_by_epic[epic_id] = []
        stories_by_epic[epic_id].append(story)

    # Generate requirements from each story - comprehensive, no arbitrary limits
    for epic_id, epic_stories in stories_by_epic.items():
        for story in epic_stories:
            req_count += 1
            actor = story.get('actor', 'User')
            action = story.get('action', 'perform action')

            # Main requirement from story
            functional.append({
                "id": f"FR-{req_count:03d}",
                "category": epic_id,
                "requirement": f"System shall allow {actor} to {action}",
                "priority": "Must Have" if req_count <= len(stories) // 2 else "Should Have",
                "source_story": story.get('id', '')
            })

            # Generate additional requirements from ALL acceptance criteria
            criteria = story.get('acceptance_criteria', [])
            for ac in criteria:  # Process all acceptance criteria, no limit
                if isinstance(ac, str) and len(ac) > 10:
                    req_count += 1
                    # Transform AC to requirement
                    ac_clean = ac.replace("The ", "System shall ensure the ").replace("User ", "user ")
                    if not ac_clean.lower().startswith("system"):
                        ac_clean = f"System shall ensure {ac_clean.lower()}"
                    functional.append({
                        "id": f"FR-{req_count:03d}",
                        "category": epic_id,
                        "requirement": ac_clean[:200],
                        "priority": "Should Have",
                        "source_story": story.get('id', '')
                    })

    # No arbitrary limit on functional requirements - generate comprehensive set

    # Derive non-functional requirements from project context, not hardcoded
    non_functional = _derive_nfrs_from_context(stories, tech_stack)

    return {
        "functional_requirements": functional,
        "non_functional_requirements": non_functional
    }


def _derive_nfrs_from_context(
    stories: List[Dict[str, Any]],
    tech_stack: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Derive non-functional requirements from project context.

    Instead of hardcoded standards, analyze the project to determine
    what NFRs are actually relevant.
    """
    non_functional = []
    nfr_count = 0

    # Analyze stories for patterns that suggest NFRs
    all_text = " ".join([
        f"{s.get('action', '')} {s.get('benefit', '')} {' '.join(s.get('acceptance_criteria', []))}"
        for s in stories
    ]).lower()

    # Check for payment/financial indicators
    if any(term in all_text for term in ['payment', 'escrow', 'money', 'transaction', 'billing', 'invoice', 'fund', 'wallet', 'credit']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Financial Security",
            "requirement": "System shall implement secure payment processing with encryption and audit logging",
            "priority": "Must Have"
        })
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Financial Compliance",
            "requirement": "System shall maintain complete audit trail of all financial transactions",
            "priority": "Must Have"
        })

    # Check for authentication/user management
    if any(term in all_text for term in ['login', 'register', 'password', 'authenticate', 'account', 'sign up', 'sign in']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Authentication Security",
            "requirement": "System shall protect user credentials using industry-standard hashing algorithms",
            "priority": "Must Have"
        })

    # Check for sensitive data handling
    if any(term in all_text for term in ['profile', 'personal', 'email', 'phone', 'address', 'identity', 'document']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Data Protection",
            "requirement": "System shall encrypt personally identifiable information at rest and in transit",
            "priority": "Must Have"
        })

    # Check for messaging/communication
    if any(term in all_text for term in ['message', 'chat', 'notification', 'email', 'alert', 'communicate']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Communication Reliability",
            "requirement": "System shall ensure message delivery with confirmation and retry mechanisms",
            "priority": "Should Have"
        })

    # Check for file/document handling
    if any(term in all_text for term in ['upload', 'file', 'document', 'attachment', 'image', 'photo']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "File Security",
            "requirement": "System shall scan uploaded files for malware and validate file types",
            "priority": "Must Have"
        })

    # Check for search/discovery
    if any(term in all_text for term in ['search', 'find', 'filter', 'browse', 'discover']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Search Performance",
            "requirement": "System shall return search results within 2 seconds for typical queries",
            "priority": "Should Have"
        })

    # Check for real-time features
    if any(term in all_text for term in ['real-time', 'live', 'instant', 'immediate', 'status update']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Real-time Performance",
            "requirement": "System shall propagate real-time updates within 500ms",
            "priority": "Should Have"
        })

    # Check for rating/review systems
    if any(term in all_text for term in ['rating', 'review', 'feedback', 'reputation', 'score']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Rating Integrity",
            "requirement": "System shall prevent manipulation of ratings and reviews",
            "priority": "Must Have"
        })

    # Check for dispute/moderation
    if any(term in all_text for term in ['dispute', 'report', 'moderation', 'flag', 'abuse']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Moderation",
            "requirement": "System shall provide mechanisms for content moderation and dispute resolution",
            "priority": "Should Have"
        })

    # Check for scheduling/booking
    if any(term in all_text for term in ['schedule', 'booking', 'appointment', 'availability', 'calendar']):
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Scheduling Reliability",
            "requirement": "System shall prevent double-booking and maintain schedule consistency",
            "priority": "Must Have"
        })

    # Analyze tech stack for infrastructure NFRs
    services = tech_stack.get('services', {})
    backend = tech_stack.get('backend', '')

    if services.get('database') or 'database' in backend.lower():
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Data Integrity",
            "requirement": "System shall implement database transactions to ensure data consistency",
            "priority": "Must Have"
        })

    if services.get('cache') or 'redis' in str(services).lower():
        nfr_count += 1
        non_functional.append({
            "id": f"NFR-{nfr_count:03d}",
            "category": "Performance",
            "requirement": "System shall utilize caching to optimize response times for frequently accessed data",
            "priority": "Should Have"
        })

    # If we found no context-specific NFRs, add minimal generic ones
    if len(non_functional) == 0:
        non_functional = [
            {"id": "NFR-001", "category": "Security", "requirement": "System shall protect against common web vulnerabilities (OWASP Top 10)", "priority": "Must Have"},
            {"id": "NFR-002", "category": "Performance", "requirement": "System shall respond to user actions within acceptable time limits", "priority": "Should Have"},
        ]

    return non_functional
