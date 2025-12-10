"""Requirements Generator

Generates functional and non-functional requirements from project analysis.
Runs in parallel with other analysis steps to avoid adding latency.
"""

from typing import Dict, Any, List
import json


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

    # Build compact context
    epic_list = "\n".join([
        f"- {e.get('title') or e.get('name', 'Untitled')}: {e.get('description', '')[:100]}"
        for e in epics
    ])

    story_list = "\n".join([
        f"- As a {s.get('actor', 'User')}, {s.get('action', 'do something')}"
        for s in stories[:15]  # Limit to avoid token bloat
    ])

    tech_info = f"Frontend: {tech_stack.get('frontend', 'N/A')}, Backend: {tech_stack.get('backend', 'N/A')}"

    prompt = f"""Generate requirements for this software project.

PROJECT: {description}

FEATURES:
{epic_list or "Not specified"}

USER STORIES:
{story_list or "Not specified"}

TECH STACK: {tech_info}

Return JSON with two arrays:
1. functional_requirements - What the system must DO (FR-001 format)
2. non_functional_requirements - How well it must perform (NFR-001 format)

Format:
{{
  "functional_requirements": [
    {{"id": "FR-001", "category": "Cart", "requirement": "System shall allow users to add products to shopping cart", "priority": "Must Have"}},
    {{"id": "FR-002", "category": "Cart", "requirement": "System shall persist cart contents across sessions", "priority": "Should Have"}}
  ],
  "non_functional_requirements": [
    {{"id": "NFR-001", "category": "Performance", "requirement": "Page load time shall not exceed 3 seconds", "priority": "Must Have"}},
    {{"id": "NFR-002", "category": "Security", "requirement": "All API endpoints shall require authentication", "priority": "Must Have"}}
  ]
}}

Rules:
- 8-15 functional requirements covering key user actions
- 5-8 non-functional requirements (security, performance, scalability, usability)
- Priority: "Must Have", "Should Have", or "Could Have"
- Use "shall" language for requirements
- Be specific and measurable where possible

Return ONLY valid JSON."""

    try:
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
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
    """Generate basic requirements from stories when LLM fails."""

    functional = []
    for i, story in enumerate(stories[:10], 1):
        actor = story.get('actor', 'User')
        action = story.get('action', 'perform action')
        functional.append({
            "id": f"FR-{i:03d}",
            "category": "Core",
            "requirement": f"System shall allow {actor} to {action}",
            "priority": "Must Have" if i <= 5 else "Should Have"
        })

    # Standard non-functional requirements
    non_functional = [
        {"id": "NFR-001", "category": "Security", "requirement": "System shall authenticate all users before granting access", "priority": "Must Have"},
        {"id": "NFR-002", "category": "Security", "requirement": "System shall encrypt sensitive data in transit and at rest", "priority": "Must Have"},
        {"id": "NFR-003", "category": "Performance", "requirement": "System shall respond to user actions within 2 seconds", "priority": "Should Have"},
        {"id": "NFR-004", "category": "Availability", "requirement": "System shall maintain 99.5% uptime", "priority": "Should Have"},
        {"id": "NFR-005", "category": "Usability", "requirement": "System shall be accessible on mobile and desktop devices", "priority": "Should Have"},
    ]

    return {
        "functional_requirements": functional,
        "non_functional_requirements": non_functional
    }
