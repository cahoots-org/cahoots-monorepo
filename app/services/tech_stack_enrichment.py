"""Tech Stack Enrichment Service

Automatically infers tech stack from:
1. User-provided GitHub repository (highest priority)
2. LLM inference from task description
3. User preferences (override)
"""

from typing import Dict, Any, Optional, List
from app.analyzer.llm_client import LLMClient


class TechStackEnrichmentService:
    """Enriches context with tech stack information."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def enrich_tech_stack(
        self,
        task_description: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        github_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enrich tech stack from available sources.

        Priority:
        1. GitHub repository analysis (most accurate)
        2. LLM inference from task description
        3. Merge with user preferences (user overrides)

        Args:
            task_description: The task description
            user_preferences: Optional user-provided tech preferences
            github_metadata: Optional GitHub repository metadata

        Returns:
            Enriched tech stack dictionary
        """
        tech_stack = {}

        # Step 1: Infer from GitHub repo if available
        if github_metadata:
            tech_stack = await self._infer_from_github(github_metadata)
            print(f"[TechStackEnrichment] Inferred from GitHub: {tech_stack}")

        # Step 2: Infer from task description if no GitHub repo
        if not tech_stack or not tech_stack.get("preferred_languages"):
            llm_inferred = await self._infer_from_description(task_description)
            # Merge with GitHub data (GitHub takes priority for conflicts)
            tech_stack = self._merge_tech_stacks(llm_inferred, tech_stack)
            print(f"[TechStackEnrichment] After LLM inference: {tech_stack}")

        # Step 3: Merge with user preferences (user overrides everything)
        if user_preferences:
            tech_stack = self._merge_tech_stacks(tech_stack, user_preferences)
            print(f"[TechStackEnrichment] After user preferences: {tech_stack}")

        return tech_stack

    async def _infer_from_github(self, github_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Infer tech stack from GitHub repository metadata.

        Uses:
        - Repository language statistics
        - Package files (package.json, requirements.txt, go.mod, etc.)
        - Framework detection from dependencies
        """
        tech_stack = {
            "application_type": "",
            "preferred_languages": [],
            "frameworks": {},
            "deployment_target": None
        }

        # Extract languages from GitHub API
        if languages := github_metadata.get("languages"):
            # Sort by usage (bytes of code)
            sorted_languages = sorted(
                languages.items(),
                key=lambda x: x[1],
                reverse=True
            )
            tech_stack["preferred_languages"] = [lang for lang, _ in sorted_languages[:3]]

        # Detect frameworks from dependencies
        if files := github_metadata.get("files"):
            frameworks = self._detect_frameworks_from_files(files)
            tech_stack["frameworks"] = frameworks

        # Infer application type from README or description
        if description := github_metadata.get("description"):
            app_type = self._infer_app_type(description)
            tech_stack["application_type"] = app_type

        return tech_stack

    def _detect_frameworks_from_files(self, files: Dict[str, Any]) -> Dict[str, List[str]]:
        """Detect frameworks from package files."""
        frameworks = {}

        # JavaScript/TypeScript
        if package_json := files.get("package.json"):
            js_frameworks = self._parse_package_json(package_json)
            if js_frameworks:
                frameworks["frontend"] = js_frameworks

        # Python
        if requirements := files.get("requirements.txt"):
            py_frameworks = self._parse_requirements(requirements)
            if py_frameworks:
                frameworks["backend"] = py_frameworks

        # Go
        if go_mod := files.get("go.mod"):
            go_frameworks = self._parse_go_mod(go_mod)
            if go_frameworks:
                frameworks["backend"] = go_frameworks

        return frameworks

    def _parse_package_json(self, content: str) -> List[str]:
        """Extract frameworks from package.json."""
        import json
        try:
            data = json.loads(content)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

            frameworks = []
            framework_map = {
                "react": "React",
                "vue": "Vue.js",
                "angular": "Angular",
                "next": "Next.js",
                "svelte": "Svelte",
                "express": "Express.js",
                "fastify": "Fastify",
                "nestjs": "NestJS"
            }

            for dep in deps:
                for key, name in framework_map.items():
                    if key in dep.lower():
                        frameworks.append(name)
                        break

            return frameworks[:3]  # Top 3
        except:
            return []

    def _parse_requirements(self, content: str) -> List[str]:
        """Extract frameworks from requirements.txt."""
        frameworks = []
        framework_map = {
            "django": "Django",
            "flask": "Flask",
            "fastapi": "FastAPI",
            "tornado": "Tornado",
            "pyramid": "Pyramid",
            "sqlalchemy": "SQLAlchemy",
            "celery": "Celery"
        }

        for line in content.split("\n"):
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue

            # Extract package name (before ==, >=, etc.)
            package = line.split("==")[0].split(">=")[0].split("<=")[0].strip()

            if package in framework_map:
                frameworks.append(framework_map[package])

        return frameworks[:3]

    def _parse_go_mod(self, content: str) -> List[str]:
        """Extract frameworks from go.mod."""
        frameworks = []
        framework_map = {
            "gin-gonic/gin": "Gin",
            "gofiber/fiber": "Fiber",
            "labstack/echo": "Echo",
            "gorilla/mux": "Gorilla Mux"
        }

        for line in content.split("\n"):
            line = line.strip()
            for key, name in framework_map.items():
                if key in line:
                    frameworks.append(name)

        return frameworks[:3]

    def _infer_app_type(self, description: str) -> str:
        """Infer application type from description."""
        description_lower = description.lower()

        if any(word in description_lower for word in ["api", "rest", "graphql", "backend"]):
            return "API/Backend"
        elif any(word in description_lower for word in ["web app", "website", "frontend"]):
            return "Web Application"
        elif any(word in description_lower for word in ["mobile", "ios", "android"]):
            return "Mobile Application"
        elif any(word in description_lower for word in ["cli", "command line", "terminal"]):
            return "CLI Tool"
        elif any(word in description_lower for word in ["game", "gaming"]):
            return "Game"
        else:
            return "Application"

    async def _infer_from_description(self, task_description: str) -> Dict[str, Any]:
        """
        Use LLM to infer appropriate tech stack from task description.
        """
        prompt = f"""Analyze this software project and recommend an appropriate tech stack based on its requirements and architecture.

Project: {task_description}

Consider:
- What type of application is this? (web, mobile, CLI, game, API, desktop, library)
- What are the core technical requirements? (UI, networking, persistence, real-time, graphics)
- What's the appropriate complexity level? (simple script, standard app, distributed system)
- What deployment model makes sense? (local executable, cloud service, containerized)

Provide your recommendation in JSON format:
{{
  "application_type": "string describing the type",
  "preferred_languages": ["language(s) that fit the requirements"],
  "frameworks": {{
    "frontend": ["only if UI is needed"],
    "backend": ["only if server/API is needed"],
    "database": ["only if persistent storage is needed"]
  }},
  "deployment_target": "Local|Docker|AWS|GCP|Vercel|Heroku|etc."
}}

Match the technology choices to the project's actual needs. Don't over-engineer simple projects, but also don't under-engineer complex ones.
"""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            import json
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                data = self.llm._parse_json(content)
            else:
                data = json.loads(response.strip())

            return data

        except Exception as e:
            print(f"[TechStackEnrichment] Error inferring from description: {e}")
            # Return sensible defaults
            return {
                "application_type": "Application",
                "preferred_languages": ["Python"],
                "frameworks": {},
                "deployment_target": None
            }

    def _merge_tech_stacks(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two tech stack dictionaries.
        Override takes precedence for non-empty values.
        """
        if not base:
            return override or {}
        if not override:
            return base or {}

        merged = base.copy()

        # Override simple fields if present
        for key in ["application_type", "tech_stack_id", "github_repo",
                    "additional_requirements", "deployment_target"]:
            if override.get(key):
                merged[key] = override[key]

        # Merge languages (override takes precedence, then append base)
        override_langs = override.get("preferred_languages", [])
        base_langs = merged.get("preferred_languages", [])
        if override_langs:
            # Keep override languages first, add unique base languages
            merged["preferred_languages"] = override_langs + [
                lang for lang in base_langs if lang not in override_langs
            ]

        # Merge frameworks (deep merge by category)
        base_frameworks = merged.get("frameworks", {})
        override_frameworks = override.get("frameworks", {})
        if override_frameworks:
            merged_frameworks = base_frameworks.copy()
            for category, frameworks in override_frameworks.items():
                if frameworks:  # Only override if non-empty
                    merged_frameworks[category] = frameworks
            merged["frameworks"] = merged_frameworks

        return merged
