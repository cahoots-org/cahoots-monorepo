"""Advanced GitHub repository analyzer for understanding codebase structure."""

import os
import re
import ast
import json
import httpx
import base64
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class CodeComponent:
    """Represents a significant code component in the repository."""
    name: str
    type: str  # 'class', 'function', 'route', 'component', 'model'
    file_path: str
    imports: List[str]
    exports: List[str]
    description: Optional[str] = None
    dependencies: List[str] = None
    methods: List[str] = None


@dataclass
class RepositoryMap:
    """Complete map of repository structure and patterns."""
    entry_points: List[str]
    core_models: List[CodeComponent]
    api_routes: Dict[str, List[str]]  # endpoint -> [methods]
    services: List[CodeComponent]
    frontend_components: List[CodeComponent]
    file_patterns: Dict[str, List[str]]  # pattern type -> example files
    dependencies: Dict[str, Set[str]]  # file -> imported files
    extension_points: Dict[str, str]  # where to add new features
    tech_stack_details: Dict[str, Any]


class GitHubRepositoryAnalyzer:
    """Analyzes GitHub repositories to create detailed code maps."""

    def __init__(self, github_token: Optional[str] = None):
        """Initialize analyzer with optional GitHub token."""
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Cahoots-Repository-Analyzer"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

        self.base_url = "https://api.github.com"

    async def analyze_repository(self, owner: str, repo: str) -> RepositoryMap:
        """Create a comprehensive map of the repository structure.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Complete repository map with architectural insights
        """
        repo_map = RepositoryMap(
            entry_points=[],
            core_models=[],
            api_routes={},
            services=[],
            frontend_components=[],
            file_patterns=defaultdict(list),
            dependencies=defaultdict(set),
            extension_points={},
            tech_stack_details={}
        )

        async with httpx.AsyncClient() as client:
            # 1. Identify entry points
            entry_points = await self._find_entry_points(client, owner, repo)
            repo_map.entry_points = entry_points

            # 2. Analyze backend structure (Python)
            if await self._has_python_backend(client, owner, repo):
                # Find FastAPI/Flask routes
                routes = await self._analyze_api_routes(client, owner, repo)
                repo_map.api_routes = routes

                # Find models/schemas
                models = await self._analyze_python_models(client, owner, repo)
                repo_map.core_models.extend(models)

                # Find services/processors
                services = await self._analyze_python_services(client, owner, repo)
                repo_map.services.extend(services)

            # 3. Analyze frontend structure (React/JS)
            if await self._has_javascript_frontend(client, owner, repo):
                components = await self._analyze_react_components(client, owner, repo)
                repo_map.frontend_components.extend(components)

            # 4. Identify extension patterns
            extension_points = await self._identify_extension_points(client, owner, repo)
            repo_map.extension_points = extension_points

            # 5. Extract tech stack details
            tech_details = await self._analyze_tech_stack(client, owner, repo)
            repo_map.tech_stack_details = tech_details

        return repo_map

    async def _find_entry_points(self, client: httpx.AsyncClient, owner: str, repo: str) -> List[str]:
        """Find application entry points."""
        entry_points = []

        # Common entry point patterns
        patterns = [
            "main.py", "app.py", "server.py", "index.py",  # Python
            "index.js", "app.js", "server.js", "index.tsx",  # JavaScript
            "docker-compose.yml", "Dockerfile"  # Docker
        ]

        for pattern in patterns:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents",
                headers=self.headers,
                params={"path": ""},
                timeout=10.0
            )

            if response.status_code == 200:
                contents = response.json()
                for item in contents:
                    if pattern in item.get("name", "").lower():
                        entry_points.append(item.get("path"))

                # Check common subdirectories
                for subdir in ["app", "src", "frontend", "backend"]:
                    subdir_response = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}/contents/{subdir}",
                        headers=self.headers,
                        timeout=10.0
                    )
                    if subdir_response.status_code == 200:
                        subdir_contents = subdir_response.json()
                        for item in subdir_contents:
                            if pattern in item.get("name", "").lower():
                                entry_points.append(item.get("path"))

        return entry_points

    async def _analyze_api_routes(self, client: httpx.AsyncClient, owner: str, repo: str) -> Dict[str, List[str]]:
        """Analyze API routes in Python backend."""
        routes = {}

        # Look for route files
        route_patterns = ["routes", "endpoints", "api", "views", "handlers"]

        for pattern in route_patterns:
            search_response = await client.get(
                f"{self.base_url}/search/code",
                headers=self.headers,
                params={
                    "q": f"@router.post OR @router.get OR @app.route repo:{owner}/{repo}",
                    "per_page": 30
                },
                timeout=10.0
            )

            if search_response.status_code == 200:
                results = search_response.json()
                for item in results.get("items", []):
                    file_path = item.get("path")
                    if file_path:
                        # Fetch file content to extract routes
                        file_content = await self._get_file_content(client, owner, repo, file_path)
                        if file_content:
                            extracted_routes = self._extract_routes_from_python(file_content)
                            routes.update(extracted_routes)

        return routes

    async def _analyze_python_models(self, client: httpx.AsyncClient, owner: str, repo: str) -> List[CodeComponent]:
        """Find and analyze Python model definitions."""
        models = []

        # Search for Pydantic models, SQLAlchemy models, dataclasses
        search_queries = [
            "class.*BaseModel repo:",
            "class.*db.Model repo:",
            "@dataclass repo:"
        ]

        for query_base in search_queries:
            query = f"{query_base}{owner}/{repo}"
            search_response = await client.get(
                f"{self.base_url}/search/code",
                headers=self.headers,
                params={"q": query, "per_page": 20},
                timeout=10.0
            )

            if search_response.status_code == 200:
                results = search_response.json()
                for item in results.get("items", [])[:10]:  # Limit to avoid rate limits
                    file_path = item.get("path")
                    if file_path and "model" in file_path.lower():
                        file_content = await self._get_file_content(client, owner, repo, file_path)
                        if file_content:
                            extracted_models = self._extract_python_classes(file_content, file_path)
                            models.extend(extracted_models)

        return models

    async def _analyze_python_services(self, client: httpx.AsyncClient, owner: str, repo: str) -> List[CodeComponent]:
        """Find and analyze service/processor classes."""
        services = []

        # Look for service patterns
        patterns = ["Service", "Processor", "Handler", "Manager", "Controller"]

        for pattern in patterns:
            search_response = await client.get(
                f"{self.base_url}/search/code",
                headers=self.headers,
                params={
                    "q": f"class.*{pattern} repo:{owner}/{repo}",
                    "per_page": 15
                },
                timeout=10.0
            )

            if search_response.status_code == 200:
                results = search_response.json()
                for item in results.get("items", [])[:5]:
                    file_path = item.get("path")
                    if file_path:
                        file_content = await self._get_file_content(client, owner, repo, file_path)
                        if file_content:
                            extracted_services = self._extract_python_classes(file_content, file_path)
                            services.extend(extracted_services)

        return services

    async def _analyze_react_components(self, client: httpx.AsyncClient, owner: str, repo: str) -> List[CodeComponent]:
        """Find and analyze React components."""
        components = []

        # Search for React components
        search_response = await client.get(
            f"{self.base_url}/search/code",
            headers=self.headers,
            params={
                "q": f"export default OR React.Component OR function.*return.*jsx repo:{owner}/{repo}",
                "per_page": 20
            },
            timeout=10.0
        )

        if search_response.status_code == 200:
            results = search_response.json()
            for item in results.get("items", [])[:10]:
                file_path = item.get("path")
                if file_path and (".jsx" in file_path or ".tsx" in file_path or "component" in file_path.lower()):
                    # Create component entry
                    component_name = os.path.basename(file_path).replace(".js", "").replace(".jsx", "").replace(".tsx", "")
                    components.append(CodeComponent(
                        name=component_name,
                        type="react_component",
                        file_path=file_path,
                        imports=[],
                        exports=[component_name]
                    ))

        return components

    async def _identify_extension_points(self, client: httpx.AsyncClient, owner: str, repo: str) -> Dict[str, str]:
        """Identify where new features should be added."""
        extension_points = {}

        # Check common patterns
        paths_to_check = {
            "app/api/routes": "Add new API endpoints here",
            "app/models": "Define new data models here",
            "app/services": "Add new business logic services here",
            "app/analyzer": "Add new analysis modules here",
            "app/processor": "Add new processing logic here",
            "frontend/src/pages": "Add new page components here",
            "frontend/src/components": "Add reusable UI components here",
            "tests": "Add test files here"
        }

        for path, description in paths_to_check.items():
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                timeout=10.0
            )
            if response.status_code == 200:
                extension_points[path] = description

        return extension_points

    async def _analyze_tech_stack(self, client: httpx.AsyncClient, owner: str, repo: str) -> Dict[str, Any]:
        """Analyze the technology stack in detail."""
        tech_stack = {
            "backend": {},
            "frontend": {},
            "database": {},
            "infrastructure": {}
        }

        # Check Python requirements
        req_response = await client.get(
            f"{self.base_url}/repos/{owner}/{repo}/contents/requirements.txt",
            headers=self.headers,
            timeout=10.0
        )
        if req_response.status_code == 200:
            content = base64.b64decode(req_response.json()["content"]).decode("utf-8")
            tech_stack["backend"]["framework"] = "FastAPI" if "fastapi" in content else "Flask" if "flask" in content else "Python"
            tech_stack["backend"]["key_libraries"] = [
                line.split("==")[0] for line in content.split("\n")[:10]
                if line and not line.startswith("#")
            ]

        # Check package.json
        pkg_response = await client.get(
            f"{self.base_url}/repos/{owner}/{repo}/contents/package.json",
            headers=self.headers,
            timeout=10.0
        )
        if pkg_response.status_code == 200:
            content = json.loads(base64.b64decode(pkg_response.json()["content"]).decode("utf-8"))
            deps = content.get("dependencies", {})
            tech_stack["frontend"]["framework"] = "React" if "react" in deps else "Vue" if "vue" in deps else "JavaScript"
            tech_stack["frontend"]["key_libraries"] = list(deps.keys())[:10]

        # Check Docker
        docker_response = await client.get(
            f"{self.base_url}/repos/{owner}/{repo}/contents/docker-compose.yml",
            headers=self.headers,
            timeout=10.0
        )
        if docker_response.status_code == 200:
            content = base64.b64decode(docker_response.json()["content"]).decode("utf-8")
            tech_stack["infrastructure"]["containerized"] = True
            if "redis" in content:
                tech_stack["database"]["cache"] = "Redis"
            if "postgres" in content:
                tech_stack["database"]["primary"] = "PostgreSQL"
            elif "mysql" in content:
                tech_stack["database"]["primary"] = "MySQL"

        return tech_stack

    async def _get_file_content(self, client: httpx.AsyncClient, owner: str, repo: str, path: str) -> Optional[str]:
        """Fetch file content from GitHub."""
        try:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                timeout=10.0
            )
            if response.status_code == 200:
                content = response.json().get("content")
                if content:
                    return base64.b64decode(content).decode("utf-8")
        except Exception:
            pass
        return None

    def _extract_routes_from_python(self, content: str) -> Dict[str, List[str]]:
        """Extract API routes from Python file content."""
        routes = {}

        # FastAPI patterns
        fastapi_pattern = r'@router\.(get|post|put|delete|patch)\("([^"]+)"'
        for match in re.finditer(fastapi_pattern, content):
            method, path = match.groups()
            if path not in routes:
                routes[path] = []
            routes[path].append(method.upper())

        # Flask patterns
        flask_pattern = r'@app\.route\("([^"]+)".*methods=\[([^\]]+)\]'
        for match in re.finditer(flask_pattern, content):
            path, methods = match.groups()
            routes[path] = [m.strip().strip("'\"") for m in methods.split(",")]

        return routes

    def _extract_python_classes(self, content: str, file_path: str) -> List[CodeComponent]:
        """Extract class definitions from Python file."""
        classes = []

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]

                    # Determine type
                    component_type = "class"
                    if "Model" in node.name or "Schema" in node.name:
                        component_type = "model"
                    elif "Service" in node.name or "Processor" in node.name:
                        component_type = "service"

                    classes.append(CodeComponent(
                        name=node.name,
                        type=component_type,
                        file_path=file_path,
                        imports=[],
                        exports=[node.name],
                        methods=methods[:5]  # Limit methods shown
                    ))
        except Exception:
            pass

        return classes

    def format_repository_map_for_llm(self, repo_map: RepositoryMap) -> str:
        """Format repository map into LLM-friendly context."""
        lines = ["=== REPOSITORY ARCHITECTURE MAP ===\n"]

        # Entry points
        if repo_map.entry_points:
            lines.append("📍 ENTRY POINTS:")
            for entry in repo_map.entry_points[:5]:
                lines.append(f"  - {entry}")
            lines.append("")

        # Core models
        if repo_map.core_models:
            lines.append("📊 CORE DATA MODELS:")
            for model in repo_map.core_models[:10]:
                lines.append(f"  - {model.name} ({model.file_path})")
                if model.methods:
                    lines.append(f"    Methods: {', '.join(model.methods[:3])}")
            lines.append("")

        # API routes
        if repo_map.api_routes:
            lines.append("🌐 API ENDPOINTS:")
            for endpoint, methods in list(repo_map.api_routes.items())[:10]:
                lines.append(f"  - {endpoint}: {', '.join(methods)}")
            lines.append("")

        # Services
        if repo_map.services:
            lines.append("⚙️ SERVICES/PROCESSORS:")
            for service in repo_map.services[:8]:
                lines.append(f"  - {service.name} ({service.file_path})")
                if service.methods:
                    lines.append(f"    Key methods: {', '.join(service.methods[:3])}")
            lines.append("")

        # Extension points
        if repo_map.extension_points:
            lines.append("🔧 WHERE TO ADD NEW FEATURES:")
            for path, description in repo_map.extension_points.items():
                lines.append(f"  - {path}: {description}")
            lines.append("")

        # Tech stack
        if repo_map.tech_stack_details:
            lines.append("💻 TECHNOLOGY STACK:")
            if backend := repo_map.tech_stack_details.get("backend"):
                lines.append(f"  Backend: {backend.get('framework', 'Unknown')}")
                if libs := backend.get("key_libraries"):
                    lines.append(f"    Libraries: {', '.join(libs[:5])}")
            if frontend := repo_map.tech_stack_details.get("frontend"):
                lines.append(f"  Frontend: {frontend.get('framework', 'Unknown')}")
            if database := repo_map.tech_stack_details.get("database"):
                lines.append(f"  Database: {database.get('primary', 'Unknown')}")
                if cache := database.get("cache"):
                    lines.append(f"    Cache: {cache}")
            lines.append("")

        # Implementation patterns
        lines.append("📝 IMPLEMENTATION PATTERNS:")
        lines.append("  When adding new features to this codebase:")
        lines.append("  1. Models go in app/models/")
        lines.append("  2. API routes go in app/api/routes/")
        lines.append("  3. Business logic goes in app/services/ or app/processor/")
        lines.append("  4. Frontend components go in frontend/src/components/")
        lines.append("  5. Pages go in frontend/src/pages/")
        lines.append("")
        lines.append("  Follow existing patterns - look at similar files for examples.")

        return "\n".join(lines)