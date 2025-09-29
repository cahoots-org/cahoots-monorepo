"""Service for fetching and processing GitHub repository metadata."""

import os
import re
import httpx
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime


class GitHubMetadataService:
    """Service for fetching repository metadata from GitHub."""

    def __init__(self):
        """Initialize the GitHub metadata service."""
        self.base_url = "https://api.github.com"
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Cahoots-Project-Manager"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def extract_repo_info(self, github_url: str) -> Optional[tuple[str, str]]:
        """Extract owner and repository name from GitHub URL.

        Args:
            github_url: GitHub repository URL or owner/repo format

        Returns:
            Tuple of (owner, repo) or None if invalid
        """
        if not github_url:
            return None

        # Clean the URL
        github_url = github_url.strip()

        # Patterns to match various GitHub URL formats
        patterns = [
            r"github\.com[/:]([^/]+)/([^/\s\.]+)",  # Standard HTTPS/SSH URLs
            r"^([^/\s]+)/([^/\s]+)$"  # Simple owner/repo format
        ]

        for pattern in patterns:
            match = re.search(pattern, github_url)
            if match:
                owner, repo = match.groups()
                # Remove .git extension if present
                repo = repo.rstrip(".git")
                return owner, repo

        return None

    async def fetch_code_samples(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """Fetch sample code files to understand patterns.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within repository

        Returns:
            List of code samples with content
        """
        samples = []

        async with httpx.AsyncClient() as client:
            try:
                # Get contents of specific path
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    contents = response.json()

                    # Look for key integration/pattern files
                    important_patterns = [
                        "integrations", "api", "routes", "services",
                        "controllers", "handlers", "models", "schemas"
                    ]

                    for item in contents[:20]:  # Limit to prevent too many API calls
                        if item.get("type") == "dir":
                            # Check if it's an important directory
                            if any(pattern in item["name"].lower() for pattern in important_patterns):
                                # Recursively fetch one level deeper
                                subpath = item.get("path", "")
                                sub_response = await client.get(
                                    f"{self.base_url}/repos/{owner}/{repo}/contents/{subpath}",
                                    headers=self.headers,
                                    timeout=10.0
                                )
                                if sub_response.status_code == 200:
                                    sub_contents = sub_response.json()
                                    # Get first few files as examples
                                    for sub_item in sub_contents[:3]:
                                        if sub_item.get("type") == "file" and sub_item.get("size", 0) < 10000:
                                            samples.append({
                                                "path": sub_item.get("path"),
                                                "name": sub_item.get("name"),
                                                "type": "pattern_file"
                                            })

                        elif item.get("type") == "file":
                            # Get sample implementation files
                            filename = item.get("name", "").lower()
                            if any(ext in filename for ext in [".py", ".js", ".ts", ".java", ".go"]):
                                if "integration" in filename or "api" in filename or "route" in filename:
                                    if item.get("size", 0) < 10000:  # Skip huge files
                                        # Fetch actual content
                                        file_response = await client.get(
                                            item.get("url"),
                                            headers=self.headers,
                                            timeout=10.0
                                        )
                                        if file_response.status_code == 200:
                                            file_data = file_response.json()
                                            if content := file_data.get("content"):
                                                decoded = base64.b64decode(content).decode("utf-8")
                                                # Get first 100 lines as sample
                                                lines = decoded.split("\n")[:100]
                                                samples.append({
                                                    "path": item.get("path"),
                                                    "name": item.get("name"),
                                                    "content_sample": "\n".join(lines),
                                                    "type": "code_sample"
                                                })

            except Exception as e:
                print(f"Error fetching code samples: {e}")

        return samples

    async def fetch_repository_summary(self, github_url: str) -> Dict[str, Any]:
        """Fetch a concise summary of repository information for task decomposition.

        Args:
            github_url: GitHub repository URL

        Returns:
            Dictionary containing repository summary
        """
        repo_info = self.extract_repo_info(github_url)
        if not repo_info:
            return {
                "error": "Invalid GitHub URL format",
                "url": github_url
            }

        owner, repo = repo_info
        summary = {
            "owner": owner,
            "repo": repo,
            "url": f"https://github.com/{owner}/{repo}",
            "fetched_at": datetime.utcnow().isoformat()
        }

        async with httpx.AsyncClient() as client:
            try:
                # Fetch main repository information
                repo_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}",
                    headers=self.headers,
                    timeout=10.0
                )

                if repo_response.status_code == 200:
                    repo_data = repo_response.json()

                    # Extract key information
                    summary.update({
                        "name": repo_data.get("name"),
                        "description": repo_data.get("description"),
                        "primary_language": repo_data.get("language"),
                        "topics": repo_data.get("topics", []),
                        "default_branch": repo_data.get("default_branch", "main"),
                        "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
                        "is_template": repo_data.get("is_template", False),
                        "archived": repo_data.get("archived", False),
                        "size_kb": repo_data.get("size", 0)
                    })

                    # Fetch language breakdown
                    languages_response = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}/languages",
                        headers=self.headers,
                        timeout=10.0
                    )

                    if languages_response.status_code == 200:
                        languages = languages_response.json()
                        if languages:
                            total = sum(languages.values())
                            # Get top 5 languages by percentage
                            lang_percentages = sorted(
                                [(lang, round((bytes_count / total) * 100, 1))
                                 for lang, bytes_count in languages.items()],
                                key=lambda x: x[1],
                                reverse=True
                            )[:5]
                            summary["languages"] = dict(lang_percentages)

                    # Fetch README excerpt
                    readme_response = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}/readme",
                        headers=self.headers,
                        timeout=10.0
                    )

                    if readme_response.status_code == 200:
                        readme_data = readme_response.json()
                        if readme_content := readme_data.get("content"):
                            # Decode base64 content
                            decoded = base64.b64decode(readme_content).decode("utf-8")
                            # Extract first meaningful paragraph (skip badges/headers)
                            lines = decoded.split("\n")
                            readme_excerpt = []
                            capturing = False

                            for line in lines:
                                # Skip badge lines and empty lines at start
                                if not capturing:
                                    if line.strip() and not line.startswith("![") and not line.startswith("#"):
                                        capturing = True

                                if capturing:
                                    readme_excerpt.append(line)
                                    # Stop after ~500 chars
                                    if sum(len(l) for l in readme_excerpt) > 500:
                                        break

                            if readme_excerpt:
                                summary["readme_excerpt"] = "\n".join(readme_excerpt[:10])

                    # Fetch directory structure (top level only)
                    contents_response = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}/contents",
                        headers=self.headers,
                        timeout=10.0
                    )

                    if contents_response.status_code == 200:
                        contents = contents_response.json()

                        directories = []
                        config_files = []

                        for item in contents:
                            if item.get("type") == "dir":
                                directories.append(item.get("name"))
                            else:
                                filename = item.get("name", "")
                                # Identify important configuration files
                                important_files = [
                                    "package.json", "requirements.txt", "pyproject.toml",
                                    "Gemfile", "pom.xml", "build.gradle", "Cargo.toml",
                                    "go.mod", "composer.json", "Makefile",
                                    "docker-compose.yml", "Dockerfile", ".dockerignore",
                                    "tsconfig.json", "webpack.config.js", "vite.config.js",
                                    ".env.example", ".env.sample"
                                ]
                                if filename in important_files:
                                    config_files.append(filename)

                        summary["structure"] = {
                            "directories": directories[:15],  # Top 15 directories
                            "config_files": config_files
                        }

                        # Infer project type from config files
                        project_types = []
                        if "package.json" in config_files:
                            project_types.append("Node.js/JavaScript")
                        if "requirements.txt" in config_files or "pyproject.toml" in config_files:
                            project_types.append("Python")
                        if "Gemfile" in config_files:
                            project_types.append("Ruby")
                        if "pom.xml" in config_files or "build.gradle" in config_files:
                            project_types.append("Java")
                        if "Cargo.toml" in config_files:
                            project_types.append("Rust")
                        if "go.mod" in config_files:
                            project_types.append("Go")
                        if "composer.json" in config_files:
                            project_types.append("PHP")
                        if "Dockerfile" in config_files or "docker-compose.yml" in config_files:
                            project_types.append("Docker")

                        summary["detected_project_types"] = project_types

                    # Fetch code samples to understand patterns
                    code_samples = await self.fetch_code_samples(owner, repo)
                    if code_samples:
                        summary["code_patterns"] = code_samples

                elif repo_response.status_code == 404:
                    summary["error"] = "Repository not found"
                elif repo_response.status_code == 403:
                    summary["error"] = "API rate limit exceeded or authentication required"
                else:
                    summary["error"] = f"GitHub API error: {repo_response.status_code}"

            except httpx.TimeoutException:
                summary["error"] = "GitHub API request timed out"
            except Exception as e:
                summary["error"] = f"Error fetching repository: {str(e)}"

        return summary

    def format_summary_for_llm(self, summary: Dict[str, Any]) -> str:
        """Format repository summary for LLM context.

        Args:
            summary: Repository summary dictionary

        Returns:
            Formatted context string for the LLM
        """
        if error := summary.get("error"):
            return f"[GitHub Repository Error: {error}]"

        parts = []

        # Header
        parts.append(f"=== GitHub Repository Context ===")
        parts.append(f"Repository: {summary['owner']}/{summary['repo']}")

        # Description
        if desc := summary.get("description"):
            parts.append(f"Description: {desc}")

        # Project types and languages
        if project_types := summary.get("detected_project_types"):
            parts.append(f"Project Type(s): {', '.join(project_types)}")

        if primary_lang := summary.get("primary_language"):
            parts.append(f"Primary Language: {primary_lang}")

        if languages := summary.get("languages"):
            lang_str = ", ".join([f"{lang} ({pct}%)" for lang, pct in languages.items()])
            parts.append(f"Language Breakdown: {lang_str}")

        # Topics (tags)
        if topics := summary.get("topics"):
            parts.append(f"Topics/Tags: {', '.join(topics)}")

        # License
        if license := summary.get("license"):
            parts.append(f"License: {license}")

        # Project structure
        if structure := summary.get("structure"):
            if dirs := structure.get("directories"):
                # Show key directories
                important_dirs = [d for d in dirs if d in [
                    "src", "app", "lib", "components", "pages", "api",
                    "tests", "test", "spec", "docs", "scripts", "config",
                    "public", "static", "assets", "styles"
                ]]
                if important_dirs:
                    parts.append(f"Key Directories: {', '.join(important_dirs)}")

            if configs := structure.get("config_files"):
                parts.append(f"Config Files: {', '.join(configs[:10])}")

        # README excerpt
        if readme := summary.get("readme_excerpt"):
            # Clean and truncate
            readme_lines = readme.strip().split("\n")[:5]
            readme_short = "\n".join(readme_lines)
            if len(readme_short) > 300:
                readme_short = readme_short[:300] + "..."
            parts.append(f"\nREADME Excerpt:\n{readme_short}")

        # Code patterns and examples
        if code_patterns := summary.get("code_patterns"):
            parts.append("\n=== Existing Code Patterns to Follow ===")

            # Group by type
            pattern_files = [p for p in code_patterns if p.get("type") == "pattern_file"]
            code_samples = [p for p in code_patterns if p.get("type") == "code_sample"]

            if pattern_files:
                parts.append("Relevant Files Found:")
                for pf in pattern_files[:5]:
                    parts.append(f"  - {pf['path']}")

            if code_samples:
                parts.append("\nCode Structure Examples:")
                for sample in code_samples[:2]:  # Show max 2 samples
                    parts.append(f"\nFrom {sample['path']}:")
                    if content := sample.get("content_sample"):
                        # Show first 30 lines to understand pattern
                        lines = content.split("\n")[:30]
                        parts.append("```")
                        parts.append("\n".join(lines))
                        parts.append("```")

            parts.append("\nIMPORTANT: Follow the patterns and structure shown above when decomposing tasks.")

        # Status flags
        flags = []
        if summary.get("archived"):
            flags.append("ARCHIVED")
        if summary.get("is_template"):
            flags.append("TEMPLATE")
        if flags:
            parts.append(f"Status: {', '.join(flags)}")

        parts.append("=" * 30)

        return "\n".join(parts)