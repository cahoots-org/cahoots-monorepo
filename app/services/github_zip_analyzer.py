"""GitHub repository analyzer using ZIP archives instead of git clone."""

import os
import httpx
import zipfile
import tempfile
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from io import BytesIO
from contextlib import asynccontextmanager
from datetime import datetime, timedelta


class RepositoryAnalysisCache:
    """Simple in-memory cache for repository analyses."""

    def __init__(self, ttl_minutes: int = 60):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, key: str) -> Optional[Dict]:
        """Get cached analysis if not expired."""
        if key in self.cache:
            entry, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return entry
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Dict):
        """Cache analysis result."""
        self.cache[key] = (value, datetime.now())


class GitHubZipAnalyzer:
    """Analyzes GitHub repositories by downloading ZIP archives."""

    # Limits for production safety
    MAX_REPO_SIZE_MB = 100  # Don't download repos larger than this
    MAX_CONCURRENT_DOWNLOADS = 5  # Limit concurrent downloads
    DOWNLOAD_TIMEOUT_SECONDS = 30
    MAX_FILES_TO_ANALYZE = 1000  # Stop after analyzing this many files

    def __init__(self, github_token: Optional[str] = None):
        """Initialize analyzer with optional GitHub token."""
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Cahoots-Analyzer"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

        self.cache = RepositoryAnalysisCache()
        self.download_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_DOWNLOADS)

    async def analyze_repository(self, owner: str, repo: str, branch: str = "main") -> Dict[str, Any]:
        """Analyze repository by downloading and extracting ZIP archive.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch to analyze

        Returns:
            Repository analysis including structure, patterns, and components
        """
        cache_key = f"{owner}/{repo}:{branch}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            print(f"Using cached analysis for {cache_key}")
            return cached

        # Check repository size first
        repo_info = await self.get_repo_info(owner, repo)
        size_mb = repo_info.get("size", 0) / 1024  # GitHub returns KB

        if size_mb > self.MAX_REPO_SIZE_MB:
            return {
                "error": f"Repository too large ({size_mb:.1f}MB > {self.MAX_REPO_SIZE_MB}MB)",
                "suggestion": "Use API-based analysis for large repositories"
            }

        # Download and analyze with concurrency control
        async with self.download_semaphore:
            result = await self._download_and_analyze(owner, repo, branch, size_mb)

        # Cache successful results
        if not result.get("error"):
            self.cache.set(cache_key, result)

        return result

    async def get_repo_info(self, owner: str, repo: str) -> Dict:
        """Get repository metadata from GitHub API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                return {"error": f"Failed to get repo info: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to get repo info: {str(e)}"}

    async def _download_and_analyze(self, owner: str, repo: str, branch: str, size_mb: float) -> Dict:
        """Download ZIP and analyze repository."""
        print(f"Downloading {owner}/{repo} ({size_mb:.1f}MB)...")

        # GitHub provides ZIP archives at this URL pattern
        archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        # Alternative: Use API endpoint (counts against rate limit but works with private repos)
        # archive_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"

        try:
            async with httpx.AsyncClient() as client:
                # Download with timeout
                response = await client.get(
                    archive_url,
                    headers=self.headers if "api.github.com" in archive_url else {},
                    follow_redirects=True,
                    timeout=self.DOWNLOAD_TIMEOUT_SECONDS
                )

                if response.status_code != 200:
                    # Try 'master' if 'main' fails
                    if branch == "main":
                        return await self._download_and_analyze(owner, repo, "master", size_mb)
                    return {"error": f"Failed to download: HTTP {response.status_code}"}

                print(f"Downloaded {len(response.content) / 1024 / 1024:.1f}MB")

                # Analyze in memory without saving to disk
                return await self._analyze_zip_content(response.content, owner, repo)

        except httpx.TimeoutException:
            return {"error": "Download timeout - repository might be too large"}
        except Exception as e:
            return {"error": f"Download failed: {str(e)}"}

    async def _analyze_zip_content(self, zip_bytes: bytes, owner: str, repo: str) -> Dict:
        """Analyze repository from ZIP bytes."""
        analysis = {
            "owner": owner,
            "repo": repo,
            "analyzed_at": datetime.now().isoformat(),
            "structure": {},
            "patterns": {},
            "components": {},
            "statistics": {}
        }

        try:
            with zipfile.ZipFile(BytesIO(zip_bytes)) as zip_ref:
                # Get all file paths
                all_files = zip_ref.namelist()

                # Skip if too many files
                if len(all_files) > self.MAX_FILES_TO_ANALYZE * 2:
                    analysis["warning"] = f"Large repo: analyzing first {self.MAX_FILES_TO_ANALYZE} files only"

                # Analyze structure
                analysis["structure"] = self._analyze_structure(all_files[:self.MAX_FILES_TO_ANALYZE])

                # Analyze code patterns by reading specific files
                analysis["patterns"] = await self._analyze_patterns(zip_ref, all_files[:self.MAX_FILES_TO_ANALYZE])

                # Extract component information
                analysis["components"] = self._extract_components(zip_ref, all_files[:self.MAX_FILES_TO_ANALYZE])

                # Statistics
                analysis["statistics"] = {
                    "total_files": len(all_files),
                    "files_analyzed": min(len(all_files), self.MAX_FILES_TO_ANALYZE),
                    "languages": self._detect_languages(all_files)
                }

        except Exception as e:
            analysis["error"] = f"Analysis failed: {str(e)}"

        return analysis

    def _analyze_structure(self, files: List[str]) -> Dict:
        """Analyze repository structure from file paths."""
        structure = {
            "directories": set(),
            "root_files": [],
            "has_tests": False,
            "has_docs": False,
            "has_ci": False,
            "package_managers": [],
            "entry_points": []
        }

        for file_path in files:
            parts = file_path.split("/")[1:]  # Skip repo name prefix

            if len(parts) == 1:
                # Root file
                structure["root_files"].append(parts[0])

                # Detect package managers
                if parts[0] == "package.json":
                    structure["package_managers"].append("npm")
                elif parts[0] == "requirements.txt":
                    structure["package_managers"].append("pip")
                elif parts[0] == "Gemfile":
                    structure["package_managers"].append("bundler")
                elif parts[0] == "pom.xml":
                    structure["package_managers"].append("maven")

                # Detect entry points
                if parts[0] in ["main.py", "app.py", "index.js", "server.js"]:
                    structure["entry_points"].append(parts[0])

            elif len(parts) > 1:
                # Directory
                structure["directories"].add(parts[0])

                # Check for special directories
                if "test" in parts[0].lower() or "spec" in parts[0].lower():
                    structure["has_tests"] = True
                if parts[0].lower() in ["docs", "documentation"]:
                    structure["has_docs"] = True
                if parts[0] == ".github":
                    structure["has_ci"] = True

        structure["directories"] = list(structure["directories"])
        return structure

    async def _analyze_patterns(self, zip_ref: zipfile.ZipFile, files: List[str]) -> Dict:
        """Analyze code patterns by reading key files."""
        patterns = {
            "api_endpoints": [],
            "models": [],
            "components": [],
            "services": []
        }

        for file_path in files:
            if file_path.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
                try:
                    # Read file content
                    with zip_ref.open(file_path) as f:
                        content = f.read().decode('utf-8', errors='ignore')

                        # Quick pattern matching (simplified for performance)
                        if "@router." in content or "@app.route" in content:
                            patterns["api_endpoints"].append(file_path)
                        if "class.*Model" in content or "Schema" in content:
                            patterns["models"].append(file_path)
                        if "export default" in content and ("jsx" in file_path or "tsx" in file_path):
                            patterns["components"].append(file_path)
                        if "Service" in content or "Processor" in content:
                            patterns["services"].append(file_path)

                except Exception:
                    pass  # Skip files that can't be read

        # Limit results
        for key in patterns:
            patterns[key] = patterns[key][:10]

        return patterns

    def _extract_components(self, zip_ref: zipfile.ZipFile, files: List[str]) -> Dict:
        """Extract key components for understanding architecture."""
        components = {
            "has_api": False,
            "has_frontend": False,
            "has_database": False,
            "has_auth": False,
            "framework": None
        }

        # Check for common patterns
        file_set = set(files)

        # API detection
        if any("api" in f.lower() or "routes" in f.lower() for f in file_set):
            components["has_api"] = True

        # Frontend detection
        if any(f.endswith((".jsx", ".tsx", ".vue")) for f in file_set):
            components["has_frontend"] = True

        # Database detection
        if any("models" in f.lower() or "schema" in f.lower() for f in file_set):
            components["has_database"] = True

        # Auth detection
        if any("auth" in f.lower() or "login" in f.lower() for f in file_set):
            components["has_auth"] = True

        # Framework detection (simplified)
        for file_path in files[:100]:  # Check first 100 files
            if "react" in file_path.lower() or any(f.endswith((".jsx", ".tsx")) for f in [file_path]):
                components["framework"] = "React"
                break
            elif "django" in file_path.lower():
                components["framework"] = "Django"
                break
            elif "flask" in file_path.lower():
                components["framework"] = "Flask"
                break

        return components

    def _detect_languages(self, files: List[str]) -> Dict[str, int]:
        """Detect programming languages from file extensions."""
        language_counts = {}

        extension_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "React",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".rb": "Ruby",
            ".go": "Go",
            ".rs": "Rust",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".c": "C",
            ".swift": "Swift",
            ".kt": "Kotlin"
        }

        for file_path in files:
            for ext, lang in extension_map.items():
                if file_path.endswith(ext):
                    language_counts[lang] = language_counts.get(lang, 0) + 1
                    break

        # Sort by count
        return dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:5])

    def format_analysis_for_llm(self, analysis: Dict) -> str:
        """Format analysis results for LLM context."""
        if analysis.get("error"):
            return f"Repository analysis failed: {analysis['error']}"

        lines = ["=== REPOSITORY ANALYSIS (ZIP) ===\n"]

        lines.append(f"Repository: {analysis['owner']}/{analysis['repo']}")

        # Structure
        if structure := analysis.get("structure", {}):
            lines.append("\n📁 STRUCTURE:")
            if dirs := structure.get("directories"):
                lines.append(f"  Directories: {', '.join(dirs[:10])}")
            if entry := structure.get("entry_points"):
                lines.append(f"  Entry Points: {', '.join(entry)}")
            if pkg := structure.get("package_managers"):
                lines.append(f"  Package Managers: {', '.join(pkg)}")

        # Patterns
        if patterns := analysis.get("patterns", {}):
            lines.append("\n🔍 CODE PATTERNS FOUND:")
            if patterns.get("api_endpoints"):
                lines.append(f"  API Endpoints in: {len(patterns['api_endpoints'])} files")
            if patterns.get("models"):
                lines.append(f"  Data Models in: {len(patterns['models'])} files")
            if patterns.get("components"):
                lines.append(f"  UI Components in: {len(patterns['components'])} files")

        # Components
        if components := analysis.get("components", {}):
            lines.append("\n🏗️ ARCHITECTURE:")
            features = []
            if components.get("has_api"):
                features.append("API")
            if components.get("has_frontend"):
                features.append("Frontend")
            if components.get("has_database"):
                features.append("Database")
            if components.get("has_auth"):
                features.append("Authentication")
            if features:
                lines.append(f"  Features: {', '.join(features)}")
            if framework := components.get("framework"):
                lines.append(f"  Framework: {framework}")

        # Statistics
        if stats := analysis.get("statistics", {}):
            lines.append("\n📊 STATISTICS:")
            lines.append(f"  Total Files: {stats.get('total_files', 0)}")
            if langs := stats.get("languages"):
                lang_str = ", ".join([f"{lang} ({count})" for lang, count in langs.items()])
                lines.append(f"  Languages: {lang_str}")

        return "\n".join(lines)