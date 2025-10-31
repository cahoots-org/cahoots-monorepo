"""Tech Stack Decision Service

Uses LLM with tool calls to make informed decisions about third-party service selection.
Constrains technology choices to the allowed catalog.
"""

from typing import Dict, Any, List, Optional
from app.analyzer.llm_client import LLMClient
from app.services.tech_catalog import TechCatalog
import json


class TechStackDecisionService:
    """Makes tech stack decisions using LLM tool calls and constrained catalog."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.catalog = TechCatalog()

    async def determine_tech_stack(
        self,
        task_description: str,
        event_model: Optional[Dict[str, Any]] = None,
        github_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Determine the complete tech stack for a project.

        Uses LLM to analyze requirements and make informed choices from the allowed catalog.

        Args:
            task_description: Project description
            event_model: Event model with commands/events/read models
            github_context: GitHub repository context (if available)

        Returns:
            Complete tech stack configuration
        """
        # Step 1: Determine core stack (language + frameworks)
        core_stack = await self._determine_core_stack(task_description, github_context)

        # Step 2: Analyze third-party service needs
        service_needs = await self._analyze_service_needs(task_description, event_model)

        # Step 3: Select specific services via tool calls
        selected_services = await self._select_services(service_needs, core_stack)

        # Step 4: Combine into final tech stack
        final_stack = {
            **core_stack,
            "services": selected_services,
            "deployment": self._determine_deployment(core_stack, selected_services)
        }

        print(f"[TechStackDecision] Final tech stack: {json.dumps(final_stack, indent=2)}")
        return final_stack

    async def _determine_core_stack(
        self,
        task_description: str,
        github_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Determine core language and frameworks.

        Constrained to: JS/TS or Python, React/Next.js for frontend, FastAPI/Express for backend
        """
        # Build GitHub context information
        github_info = ""
        if github_context:
            repo_summary = github_context.get("repo_summary", "")
            if repo_summary:
                github_info = f"\n\nEXISTING REPOSITORY CONTEXT:\n{repo_summary[:1500]}\n\nIMPORTANT: Match the tech stack of the existing repository. If it uses React + FastAPI, use those. If it uses Next.js + Express, use those."

        # Build constraint description
        constraints = f"""
ALLOWED FRONTEND FRAMEWORKS (if frontend needed):
- "React": For SPAs, dashboards, interactive UIs (uses TypeScript/JavaScript)
- "Next.js": For SSR, static sites, SEO-friendly sites (uses TypeScript/JavaScript)

ALLOWED BACKEND FRAMEWORKS (if backend needed):
- "FastAPI": For Python APIs, microservices with async support
- "Express": For TypeScript APIs, web servers

NO OTHER FRAMEWORKS ARE SUPPORTED.
IMPORTANT: Use the EXACT string values shown above (e.g., "React" not "react").

NOTE: Languages are implicit in framework choices:
- FastAPI → Python backend
- Express → TypeScript backend
- React/Next.js → TypeScript/JavaScript frontend
"""

        prompt = f"""Analyze this project and determine the core tech stack.

PROJECT: {task_description}

{constraints}{github_info}

Determine:
1. Frontend framework: MUST be "React", "Next.js", or null - only if UI needed
2. Backend framework: MUST be "FastAPI" or "Express" or null - only if API/server needed

CRITICAL: You MUST respond with ONLY valid JSON. No explanation, no markdown, no code blocks.
Use the EXACT string values from constraints (case-sensitive).

Return this exact JSON structure:
{{
  "frontend": "React" OR "Next.js" OR null,
  "backend": "FastAPI" OR "Express" OR null,
  "justification": "Brief explanation of choices"
}}

Match technology to actual needs. Don't add frontend if it's a CLI tool or pure API.
"""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
            else:
                content = response.strip()

            print(f"[TechStackDecision] LLM raw response: {content[:200]}...")

            # Try parsing JSON
            try:
                data = self.llm._parse_json(content)
            except Exception as parse_error:
                print(f"[TechStackDecision] JSON parse failed: {parse_error}")
                print(f"[TechStackDecision] Full response: {content}")
                raise

            # Strip the "language" field if the LLM added it (we don't want it)
            if "language" in data:
                del data["language"]

            # Validate choices against catalog
            frontend = data.get("frontend")
            if frontend and frontend not in self.catalog.FRONTEND_FRAMEWORKS:
                raise ValueError(f"Invalid frontend framework: {frontend}")

            backend = data.get("backend")
            if backend and backend not in self.catalog.BACKEND_FRAMEWORKS:
                raise ValueError(f"Invalid backend framework: {backend}")

            print(f"[TechStackDecision] Core stack determined: {data}")
            return data

        except Exception as e:
            print(f"[TechStackDecision] Error determining core stack: {e}")
            # Safe default
            return {
                "frontend": None,
                "backend": "FastAPI",
                "justification": "Default stack due to error"
            }

    async def _analyze_service_needs(
        self,
        task_description: str,
        event_model: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Analyze which third-party service categories are needed.

        Returns a dictionary of service categories and whether they're needed.
        """
        # Build context from event model
        context = ""
        if event_model:
            commands = event_model.get("commands", [])
            events = event_model.get("events", [])
            read_models = event_model.get("read_models", [])

            context = f"""
EVENT MODEL ANALYSIS:
- {len(commands)} commands (user actions)
- {len(events)} events (domain events)
- {len(read_models)} read models (data queries)

Sample commands: {', '.join([c.get('name', '') for c in commands[:5]])}
Sample events: {', '.join([e.get('name', '') if isinstance(e, dict) else getattr(e, 'name', '') for e in events[:5]])}
"""

        prompt = f"""Analyze this project and determine which third-party service categories are needed.

PROJECT: {task_description}

{context}

For each category below, determine if it's needed (true/false):

CATEGORIES:
- database: Need to persist data beyond session/memory?
- cache: Need caching for performance (Redis, etc)?
- payment: Need payment processing (Stripe, PayPal)?
- auth: Need user authentication/authorization (OAuth, JWT)?
- storage: Need file/image storage (S3, Cloudinary)?
- email: Need to send emails (transactional, notifications)?
- queue: Need background job processing (async tasks)?

Return JSON:
{{
  "database": true/false,
  "cache": true/false,
  "payment": true/false,
  "auth": true/false,
  "storage": true/false,
  "email": true/false,
  "queue": true/false,
  "reasoning": "Brief explanation of needs"
}}

Be conservative - only mark as true if the feature is clearly needed based on requirements.
"""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                data = self.llm._parse_json(content)
            else:
                data = json.loads(response.strip())

            needs = {k: v for k, v in data.items() if k != "reasoning" and isinstance(v, bool)}
            print(f"[TechStackDecision] Service needs: {needs}")
            print(f"[TechStackDecision] Reasoning: {data.get('reasoning', 'N/A')}")

            return needs

        except Exception as e:
            print(f"[TechStackDecision] Error analyzing service needs: {e}")
            return {}

    async def _select_services(
        self,
        service_needs: Dict[str, bool],
        core_stack: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Select specific services for each needed category.

        Uses LLM to choose the best option from the catalog based on use case.
        """
        selected = {}

        for category, is_needed in service_needs.items():
            if not is_needed:
                continue

            # Get available options from catalog
            category_map = {
                "database": self.catalog.DATABASES,
                "cache": self.catalog.CACHING,
                "payment": self.catalog.PAYMENT_PROVIDERS,
                "auth": self.catalog.AUTH_PROVIDERS,
                "storage": self.catalog.STORAGE_PROVIDERS,
                "email": self.catalog.EMAIL_PROVIDERS,
                "queue": self.catalog.QUEUE_PROVIDERS
            }

            options = category_map.get(category, {})
            if not options:
                continue

            # Use LLM to select from catalog
            selected_service = await self._llm_select_service(category, options, core_stack)
            selected[category] = selected_service

        return selected

    async def _llm_select_service(
        self,
        category: str,
        options: Dict[str, Any],
        core_stack: Dict[str, Any]
    ) -> str:
        """Use LLM to select the best service option for a category."""

        # Format options
        options_text = []
        for name, tech in options.items():
            options_text.append(f"""
- {name}:
  Use cases: {', '.join(tech.use_cases)}
  Description: {tech.description}
  Requires service: {tech.requires_service}
""")

        backend = core_stack.get('backend', 'None')
        frontend = core_stack.get('frontend', 'None')

        # Infer language from backend framework
        language = "Python" if backend == "FastAPI" else "TypeScript" if backend == "Express" else "Unknown"

        prompt = f"""Select the best {category} option for this project.

CORE STACK:
- Backend: {backend} ({language})
- Frontend: {frontend}

AVAILABLE OPTIONS:
{''.join(options_text)}

Choose the option that best fits the use case and integrates well with the core stack.
For example:
- If using FastAPI (Python), prefer Celery for queues
- If using Express (TypeScript), prefer BullMQ for queues
- If using Next.js, consider Vercel-friendly options

Return ONLY the name of the chosen option (e.g., "PostgreSQL", "Redis", "Stripe").
No explanation, just the name.
"""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.1
            )

            if isinstance(response, dict) and "choices" in response:
                choice = response["choices"][0]["message"]["content"].strip()
            else:
                choice = response.strip()

            # Clean up response (remove quotes, periods, etc.)
            choice = choice.strip('"').strip("'").strip(".")

            # Validate choice
            if choice in options:
                print(f"[TechStackDecision] Selected {choice} for {category}")
                return choice
            else:
                # Fallback to first option
                fallback = list(options.keys())[0]
                print(f"[TechStackDecision] Invalid choice '{choice}', using fallback: {fallback}")
                return fallback

        except Exception as e:
            print(f"[TechStackDecision] Error selecting {category}: {e}")
            return list(options.keys())[0]

    def _determine_deployment(
        self,
        core_stack: Dict[str, Any],
        services: Dict[str, str]
    ) -> str:
        """Determine deployment target based on stack."""

        # If using Next.js, Vercel is a good choice
        if core_stack.get("frontend") == "Next.js":
            return "Vercel"

        # If using multiple services, Docker Compose or Kubernetes
        if len(services) > 2:
            return "Docker"

        # Otherwise, Docker is a safe default
        return "Docker"
