"""GitHub Context Enrichment Agent

Intelligently gathers context from GitHub repositories using iterative LLM-driven approach.
"""

import json
from typing import Dict, Any, List, Optional
from collections import defaultdict
from app.services.github_client import GitHubClient
from app.analyzer.llm_client import LLMClient


class GitHubContextEnrichmentAgent:
    """
    Agent that intelligently gathers context from a GitHub repository.

    Workflow:
    1. Fetch file tree (cheap, single API call)
    2. Read obvious critical files (README, package.json, etc.)
    3. Summarize initial context
    4. LLM judges if context is sufficient for user's task
    5. If insufficient, LLM requests specific files to read
    6. Iterate until context is sufficient or budget exhausted
    """

    # Critical files that are almost always relevant
    CRITICAL_FILE_PATTERNS = [
        "README.md",
        "readme.md",
        "README",
        "CONTRIBUTING.md",
        "package.json",
        "package-lock.json",
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "go.sum",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Dockerfile",
        ".env.example",
        "tsconfig.json",
        "next.config.js",
        "vite.config.ts",
        "webpack.config.js"
    ]

    def __init__(self, llm_client: LLMClient, github_token: Optional[str] = None):
        """
        Initialize the GitHub context enrichment agent.

        Args:
            llm_client: LLM client for decision-making and summarization
            github_token: Optional GitHub personal access token
        """
        self.llm = llm_client
        self.github_token = github_token
        self.file_tree: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {
            "file_summaries": {},
            "repo_summary": "",
            "tech_stack": {}
        }
        self.iteration_count = 0
        self.api_call_count = 0
        self.final_confidence = 0.0

    async def enrich_task_context(
        self,
        repo_url: str,
        user_prompt: str,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Main entry point for context enrichment.

        Args:
            repo_url: GitHub repository URL
            user_prompt: User's task description
            max_iterations: Maximum number of iterative file fetching rounds

        Returns:
            Enriched context dictionary
        """
        print(f"[GitHubContextAgent] Starting context enrichment for {repo_url}")

        async with GitHubClient(self.github_token) as github:
            # Parse repo URL
            owner, repo = github.parse_repo_url(repo_url)
            print(f"[GitHubContextAgent] Repository: {owner}/{repo}")

            # Check if repo exists and is accessible
            exists, is_public = await github.check_repo_access(owner, repo)
            if not exists:
                raise ValueError(f"Repository {owner}/{repo} not found or not accessible")

            if not is_public and not self.github_token:
                raise ValueError(f"Repository {owner}/{repo} is private. GitHub authentication required.")

            # Phase 1: Fetch tree
            print("[GitHubContextAgent] Phase 1: Fetching file tree...")
            await self._fetch_tree(github, owner, repo)

            # Phase 2: Read critical files
            print("[GitHubContextAgent] Phase 2: Reading critical files...")
            critical_files = await self._fetch_critical_files(github, owner, repo)

            # Phase 3: Summarize
            print("[GitHubContextAgent] Phase 3: Summarizing context...")
            repo_summary = await self._summarize_context(critical_files)

            # Phase 4: Identify relevant pattern files to read
            print("[GitHubContextAgent] Phase 4: Identifying relevant files to read...")
            file_analysis = await self._identify_relevant_files(user_prompt, repo_summary)

            # Phase 5: ALWAYS read pattern files if any were identified
            # This is critical - we need to understand actual code patterns, not just file names
            files_to_read = []
            if file_analysis.get("pattern_files"):
                files_to_read.extend(file_analysis["pattern_files"])
            if file_analysis.get("suggested_files"):
                files_to_read.extend(file_analysis["suggested_files"])

            # Dedupe and limit
            files_to_read = list(dict.fromkeys(files_to_read))[:15]

            if files_to_read:
                print(f"[GitHubContextAgent] Phase 5: Reading {len(files_to_read)} relevant files...")
                for file_path in files_to_read:
                    print(f"  → {file_path}")
                await self._fetch_additional_files(
                    github=github,
                    owner=owner,
                    repo=repo,
                    user_prompt=user_prompt,
                    initial_suggested_files=files_to_read,
                    max_iterations=1  # Just one pass - we already know what to read
                )
                self.final_confidence = file_analysis.get("confidence", 0.8)
            else:
                print("[GitHubContextAgent] Phase 5: No additional files identified")
                self.final_confidence = file_analysis.get("confidence", 0.6)

            # Phase 6: Build final context
            print("[GitHubContextAgent] Phase 6: Building final context...")
            final_context = await self._build_final_context(repo_url, owner, repo, is_public)

            print(f"[GitHubContextAgent] ✅ Context enrichment complete")
            print(f"  - Files read: {final_context['context_metadata']['files_read']}")
            print(f"  - API calls: {final_context['context_metadata']['api_calls_used']}")
            print(f"  - Confidence: {final_context['context_metadata']['confidence']:.2f}")

            return final_context

    async def _fetch_tree(self, github: GitHubClient, owner: str, repo: str) -> None:
        """Fetch and store the repository file tree."""
        tree_response = await github.get_tree(owner, repo, recursive=True)

        # Organize tree data
        files = tree_response.get("tree", [])
        by_path = {item["path"]: item for item in files if item["type"] == "blob"}
        by_extension = defaultdict(list)

        for item in files:
            if item["type"] == "blob":
                path = item["path"]
                if "." in path:
                    ext = path.split(".")[-1]
                    by_extension[ext].append(path)

        # Detect directories
        directories = set()
        for item in files:
            if item["type"] == "tree":
                directories.add(item["path"])

        self.file_tree = {
            "total_files": len([f for f in files if f["type"] == "blob"]),
            "files": files,
            "by_path": by_path,
            "by_extension": dict(by_extension),
            "directories": sorted(directories)
        }

        self.api_call_count += 1

    async def _fetch_critical_files(
        self,
        github: GitHubClient,
        owner: str,
        repo: str
    ) -> Dict[str, str]:
        """Fetch content of critical files (README, config files, etc.)."""
        critical_files = {}

        for pattern in self.CRITICAL_FILE_PATTERNS:
            if pattern in self.file_tree["by_path"]:
                try:
                    content = await github.get_file_content(owner, repo, pattern)
                    critical_files[pattern] = content
                    self.api_call_count += 1
                    print(f"  ✓ Read {pattern} ({len(content)} chars)")
                except Exception as e:
                    print(f"  ✗ Could not read {pattern}: {e}")

        return critical_files

    async def _summarize_context(self, critical_files: Dict[str, str]) -> str:
        """Use LLM to summarize critical files into concise context."""
        # Build tree summary
        tree_summary = {
            "total_files": self.file_tree["total_files"],
            "file_types": {ext: len(files) for ext, files in self.file_tree["by_extension"].items()},
            "key_directories": self.file_tree["directories"][:20]  # Top 20
        }

        # Format files for summary
        files_text = []
        for path, content in critical_files.items():
            # Truncate very long files
            display_content = content[:2000] if len(content) > 2000 else content
            files_text.append(f"=== {path} ===\n{display_content}\n")

        prompt = f"""Summarize this GitHub repository for task planning.

FILE TREE SUMMARY:
{json.dumps(tree_summary, indent=2)}

CRITICAL FILES:
{chr(10).join(files_text)}

Create a concise summary (max 500 words) covering:
1. What this project does (from README)
2. Tech stack and dependencies
3. Project structure and architecture
4. Key components/modules
5. Any deployment/infrastructure notes

Focus on information relevant for planning implementation tasks.
"""

        response = await self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2
        )

        if isinstance(response, dict) and "choices" in response:
            summary = response["choices"][0]["message"]["content"]
        else:
            summary = str(response)

        self.context["repo_summary"] = summary
        return summary

    async def _identify_relevant_files(
        self,
        user_prompt: str,
        repo_summary: str
    ) -> Dict[str, Any]:
        """Identify which files from the repo should be read to understand patterns."""
        # Build intelligent file tree showing directory structure
        file_tree_by_directory = defaultdict(list)
        for file_path in self.file_tree["by_path"].keys():
            if "/" in file_path:
                directory = "/".join(file_path.split("/")[:-1])
                filename = file_path.split("/")[-1]
                file_tree_by_directory[directory].append(filename)
            else:
                file_tree_by_directory["(root)"].append(file_path)

        # Format as tree structure
        tree_display = []
        for directory in sorted(file_tree_by_directory.keys()):
            files = file_tree_by_directory[directory]
            tree_display.append(f"{directory}/")
            for file in sorted(files)[:20]:  # Limit files per directory
                tree_display.append(f"  - {file}")
            if len(files) > 20:
                tree_display.append(f"  ... and {len(files) - 20} more files")

        system_prompt = """You are a senior developer analyzing a codebase to find relevant files for implementing a new feature.
Your job is to identify which existing files should be READ to understand the patterns and architecture.
Respond ONLY with valid JSON."""

        user_prompt_text = f"""FEATURE TO IMPLEMENT: {user_prompt}

REPOSITORY OVERVIEW:
{repo_summary}

COMPLETE FILE TREE:
{chr(10).join(tree_display)}

YOUR TASK: Identify the most important files to READ before implementing this feature.

Think step by step:
1. What existing features are SIMILAR to what's being requested?
   - If user says "similar to X" or "like X", find the files that implement X
   - If user wants "notifications", find existing notification/alert/email code
   - If user wants "integration", find existing integration examples

2. What are the CORE architectural files?
   - Main entry points, routers, services
   - Event handlers, processors
   - Configuration files

3. What PATTERNS should be followed?
   - How are similar services structured?
   - How do existing integrations work?
   - Where do new features get hooked in?

RESPOND WITH JSON:
{{
  "reasoning": "Brief explanation of why these files are relevant",
  "pattern_files": [
    "path/to/file1.py",  // Files showing patterns to COPY/FOLLOW
    "path/to/file2.py"   // e.g., existing integrations, similar services
  ],
  "suggested_files": [
    "path/to/file3.py",  // Files for understanding architecture
    "path/to/file4.py"   // e.g., where to hook in, config, main handlers
  ],
  "confidence": 0.0-1.0  // How confident you are these files are relevant
}}

IMPORTANT:
- List 5-10 files total (pattern_files are most important)
- Use EXACT file paths from the tree above
- If the task mentions "similar to X", you MUST find files implementing X
- Prioritize actual implementation files over config/docs"""

        result = await self.llm.generate_json(
            system_prompt,
            user_prompt_text,
            temperature=0.1
        )
        return result

    async def _fetch_additional_files(
        self,
        github: GitHubClient,
        owner: str,
        repo: str,
        user_prompt: str,
        initial_suggested_files: List[str],
        max_iterations: int = 3
    ) -> None:
        """Iteratively fetch files suggested by LLM."""
        suggested_files = initial_suggested_files

        while self.iteration_count < max_iterations and suggested_files:
            self.iteration_count += 1
            print(f"[GitHubContextAgent]   Iteration {self.iteration_count}: Fetching {len(suggested_files)} files...")

            # Fetch suggested files
            for file_path in suggested_files:
                if file_path in self.file_tree["by_path"]:
                    try:
                        content = await github.get_file_content(owner, repo, file_path)
                        self.api_call_count += 1

                        # Summarize file content (don't store raw)
                        summary = await self._summarize_file(file_path, content)
                        self.context["file_summaries"][file_path] = summary
                        print(f"    ✓ Read and summarized {file_path}")
                    except Exception as e:
                        print(f"    ✗ Could not read {file_path}: {e}")
                else:
                    print(f"    ✗ File not found: {file_path}")

            # After reading files, we're done (single pass approach)
            print(f"[GitHubContextAgent]   ✓ Completed reading {len(self.context['file_summaries'])} files")
            break

    async def _summarize_file(self, file_path: str, content: str) -> str:
        """Summarize a single file's content."""
        # Truncate very long files
        if len(content) > 3000:
            content = content[:3000] + "\n... [truncated]"

        prompt = f"""Summarize this file for task planning context.

FILE: {file_path}

CONTENT:
{content}

Provide a brief summary (max 150 words) covering:
- What this file does
- Key functions/classes/exports
- How it might be relevant for adding new features

Focus on implementation patterns and integration points.
"""

        response = await self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2
        )

        if isinstance(response, dict) and "choices" in response:
            return response["choices"][0]["message"]["content"]
        else:
            return str(response)

    def _build_enriched_summary(self) -> str:
        """Build enriched summary including all fetched files."""
        parts = [
            "REPOSITORY OVERVIEW:",
            self.context["repo_summary"],
            ""
        ]

        if self.context["file_summaries"]:
            parts.append("ADDITIONAL FILE CONTEXT:")
            for path, summary in self.context["file_summaries"].items():
                parts.append(f"\n{path}:")
                parts.append(summary)

        return "\n".join(parts)

    async def detect_feature_overlap(
        self,
        user_prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if requested features already exist in the repository.

        Args:
            user_prompt: User's task description

        Returns:
            Feature overlap analysis or None if detection not available
        """
        from app.services.feature_overlap_detector import FeatureOverlapDetector

        if not self.context["repo_summary"]:
            return None

        detector = FeatureOverlapDetector(self.llm)
        return await detector.detect_existing_features(
            user_prompt=user_prompt,
            repo_summary=self.context["repo_summary"],
            file_summaries=self.context["file_summaries"]
        )

    async def _build_final_context(
        self,
        repo_url: str,
        owner: str,
        repo: str,
        is_public: bool
    ) -> Dict[str, Any]:
        """Assemble all gathered context into structured format."""
        return {
            "repo_url": repo_url,
            "repo_info": {
                "owner": owner,
                "repo": repo,
                "is_public": is_public
            },
            "repo_summary": self.context["repo_summary"],
            "file_tree_summary": {
                "total_files": self.file_tree["total_files"],
                "file_types": {ext: len(files) for ext, files in self.file_tree["by_extension"].items()},
                "directories": self.file_tree["directories"]
            },
            "file_summaries": self.context["file_summaries"],
            "context_metadata": {
                "iterations": self.iteration_count,
                "files_read": len(self.context["file_summaries"]) + len([f for f in self.context.get("file_summaries", {})]),
                "api_calls_used": self.api_call_count,
                "confidence": self.final_confidence
            }
        }
