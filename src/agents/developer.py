# src/agents/developer.py
from .base_agent import BaseAgent
from ..services.github_service import GitHubService
from ..utils.event_system import EventSystem, CHANNELS
from ..models.task import Task
from typing import List, Dict, Any
import asyncio
import os
import uuid
import json
import time

class Developer(BaseAgent):
    def __init__(self, developer_id: str):
        """Initialize the developer agent."""
        super().__init__("codellama/CodeLlama-34b-Instruct-hf")
        self.developer_id = developer_id
        self.github = GitHubService()
        self.feedback_history = []
        self.focus = "backend development"
        
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        self.logger.info("Setting up event system")
        await self.event_system.connect()
        await self.event_system.subscribe("system", self.handle_system_message)
        await self.event_system.subscribe("story_assigned", self.handle_story_assigned)
        self._listening_task = asyncio.create_task(self.start_listening())
        self.logger.info("Event system setup complete")
        
    async def _handle_message(self, message: dict) -> Dict[str, Any]:
        """Handle a specific message type.
        
        Args:
            message: The message to handle, already decoded if it was a string.
            
        Returns:
            Dict[str, Any]: The response to the message.
            
        Raises:
            ValueError: If the message has an unknown type
        """
        if message["type"] == "new_story":
            return self.handle_new_story(message)
        elif message["type"] == "review_request":
            return self.handle_review_request(message)
        else:
            error_msg = f"Unknown message type: {message['type']}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    async def handle_story_assigned(self, data: Dict):
        """Handle story assignment event"""
        self.logger.info(f"Received story assignment: {data}")
        
        # Ensure we have all required fields
        required_fields = ["story_id", "title", "description", "repo_url", "assigned_to"]
        if not all(field in data for field in required_fields):
            self.logger.error(f"Missing required fields in story assignment. Required: {required_fields}, Got: {list(data.keys())}")
            return
            
        if data.get("assigned_to") != self.developer_id:
            self.logger.info(f"Story assigned to {data.get('assigned_to')}, but I am {self.developer_id}. Ignoring.")
            return
            
        try:
            # Create and register task
            task = Task(
                id=data["story_id"],
                title=data["title"],
                description=data["description"]
            )
            self.event_system.register_task(task)
            
            # Extract repository name from URL
            repo_url = data["repo_url"]
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            
            # Clone the repository
            self.logger.info(f"Cloning repository {repo_url}")
            repo_path = self.github.clone_repository(repo_url)
            self.logger.info(f"Repository cloned to {repo_path}")
            
            # Create a feature branch for the story
            branch_name = f"feature/{data['story_id']}"
            self.logger.info(f"Creating branch {branch_name}")
            self.github.create_branch(repo_name, branch_name)
            
            # Start work on the task
            await self.event_system.publish("task_started", {
                "task_id": task.id,
                "actor": self.developer_id,
                "details": {
                    "repo": repo_name,
                    "branch": branch_name,
                    "focus": self.focus
                }
            })
            
            # Break down story into tasks
            self.logger.info("Breaking down story into tasks")
            subtasks = self.break_down_story({
                "title": data["title"],
                "description": data["description"]
            })
            
            # Implement each subtask
            for subtask in subtasks:
                try:
                    # Create initial implementation
                    self.logger.info(f"Implementing subtask: {subtask.title}")
                    implementation = self.implement_task(subtask)
                    
                    # Commit changes
                    files = {
                        implementation["file_path"]: implementation["code"]
                    }
                    
                    self.logger.info(f"Committing changes for subtask {subtask.id}")
                    self.github.commit_changes(
                        repo_name,
                        branch_name,
                        files,
                        f"feat: {subtask.title}"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Failed to implement subtask {subtask.id}: {str(e)}")
                    await self.event_system.publish("task_blocked", {
                        "task_id": task.id,
                        "reason": str(e),
                        "blocker": {
                            "subtask_id": subtask.id,
                            "type": "implementation_error"
                        }
                    })
                    return
            
            # Create pull request
            self.logger.info("Creating pull request")
            pr_url = await self.create_pr({
                subtask.id: {
                    "code": self.implement_task(subtask)["code"],
                    "task": subtask.dict()
                } for subtask in subtasks
            })
            
            # Submit for review
            await self.event_system.publish("pr_created", {
                "task_id": task.id,
                "actor": self.developer_id,
                "pr_url": pr_url
            })
            
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            self.logger.error(f"Stack trace:", exc_info=True)
            await self.event_system.publish("task_failed", {
                "task_id": data["story_id"],
                "reason": str(e)
            })
    
    async def handle_new_story(self, message: dict) -> dict:
        """Handle new story assignment"""
        tasks = await self.break_down_story(message["story"])
        
        if self.needs_ux_design(tasks):
            return {
                "status": "needs_ux",
                "tasks": [task.dict() for task in tasks]
            }
            
        implementation_result = await self.implement_tasks(tasks)
        pr_url = await self.create_pr(implementation_result)
        
        return {
            "status": "success",
            "pr_url": pr_url,
            "implementation": implementation_result
        }
    
    async def review_code(self, pr_url: str) -> dict:
        """Review code changes in a pull request."""
        try:
            # Get PR changes
            changes = await self.github.get_pr_changes(pr_url)
            
            # Generate review prompt
            prompt = f"""Review these code changes:
            {changes}
            
            Consider:
            - Code quality and style
            - Potential bugs
            - Performance issues
            - Security concerns
            - Test coverage
            
            Format response as:
            Approved: yes/no
            Critical: list critical issues
            Non-critical: list non-critical issues
            Positive: list positive aspects
            Recommendations: list recommendations
            """
            
            review_response = await self.generate_response(prompt)
            
            # Parse review response into structured feedback
            review_result = self._parse_review_response(review_response)
            
            # Store the review feedback
            self._integrate_feedback({
                "type": "review",
                "content": review_result,
                "context": str(changes),
                "outcome": "approved" if review_result["approved"] else "changes_requested",
                "timestamp": time.time()
            })
            
            # Add review comments to PR
            await self._add_review_comments(pr_url, review_result)
            
            return review_result
            
        except Exception as e:
            self.logger.error(f"Failed to review code: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            raise

    async def _run_static_analysis(self, changes: Dict[str, str]) -> Dict[str, Any]:
        """Run static analysis on changed code."""
        results = {
            "errors": [],
            "warnings": [],
            "style_issues": []
        }
        
        for file_path, content in changes.items():
            # Run ruff for Python files
            if file_path.endswith('.py'):
                try:
                    process = await asyncio.create_subprocess_exec(
                        'ruff',
                        'check',
                        '--format=json',
                        '-',
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate(content.encode())
                    
                    if stdout:
                        issues = json.loads(stdout)
                        for issue in issues:
                            if issue["type"] == "error":
                                results["errors"].append(issue)
                            elif issue["type"] == "warning":
                                results["warnings"].append(issue)
                            else:
                                results["style_issues"].append(issue)
                                
                except Exception as e:
                    self.logger.error(f"Static analysis failed: {str(e)}")
                    
        return results
        
    async def _analyze_complexity(self, changes: Dict[str, str]) -> Dict[str, Any]:
        """Analyze code complexity metrics."""
        results = {}
        
        for file_path, content in changes.items():
            try:
                # Calculate cyclomatic complexity
                complexity = self._calculate_complexity(content)
                
                # Calculate cognitive complexity
                cognitive_score = self._calculate_cognitive_complexity(content)
                
                results[file_path] = {
                    "cyclomatic_complexity": complexity,
                    "cognitive_complexity": cognitive_score,
                    "issues": []
                }
                
                # Flag complex functions
                if complexity > 10:
                    results[file_path]["issues"].append(
                        f"High cyclomatic complexity ({complexity}). Consider breaking down the function."
                    )
                if cognitive_score > 15:
                    results[file_path]["issues"].append(
                        f"High cognitive complexity ({cognitive_score}). Simplify the logic."
                    )
                    
            except Exception as e:
                self.logger.error(f"Complexity analysis failed for {file_path}: {str(e)}")
                
        return results
        
    async def _check_test_coverage(self, changes: Dict[str, str]) -> Dict[str, Any]:
        """Check test coverage for changed code."""
        results = {
            "coverage_percentage": 0,
            "uncovered_lines": [],
            "missing_tests": []
        }
        
        try:
            # Run coverage analysis
            process = await asyncio.create_subprocess_exec(
                'coverage',
                'run',
                '-m',
                'pytest',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Generate coverage report
            process = await asyncio.create_subprocess_exec(
                'coverage',
                'json',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                coverage_data = json.loads(stdout)
                results["coverage_percentage"] = coverage_data["totals"]["percent_covered"]
                
                # Analyze coverage for changed files
                for file_path in changes:
                    if file_path in coverage_data["files"]:
                        file_coverage = coverage_data["files"][file_path]
                        results["uncovered_lines"].extend(file_coverage["missing_lines"])
                        
                        # Check for missing tests
                        if not any(t.endswith('_test.py') for t in os.listdir(os.path.dirname(file_path))):
                            results["missing_tests"].append(file_path)
                            
        except Exception as e:
            self.logger.error(f"Coverage analysis failed: {str(e)}")
            
        return results
        
    def _parse_review_response(self, review_response: str) -> Dict[str, Any]:
        """Parse the LLM review response into structured feedback."""
        lines = review_response.split('\n')
        result = {
            "approved": False,
            "critical_issues": [],
            "non_critical_issues": [],
            "positive_feedback": [],
            "recommendations": []
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "approved" in line.lower():
                result["approved"] = "approved" in line.lower() and "not" not in line.lower()
            elif line.startswith("Critical:") or line.startswith("Blocking:"):
                current_section = "critical_issues"
            elif line.startswith("Non-critical:") or line.startswith("Suggestions:"):
                current_section = "non_critical_issues"
            elif line.startswith("Positive:") or line.startswith("Good:"):
                current_section = "positive_feedback"
            elif line.startswith("Recommendation:") or line.startswith("Suggested:"):
                current_section = "recommendations"
            elif current_section and line.startswith("-"):
                result[current_section].append(line[1:].strip())
                
        return result
        
    async def _add_review_comments(self, pr_url: str, review_result: Dict[str, Any]):
        """Add review comments to the PR."""
        comment = "## Code Review Results\n\n"
        
        if review_result["approved"]:
            comment += "✅ Approved\n\n"
        else:
            comment += "❌ Changes Requested\n\n"
            
        if review_result["critical_issues"]:
            comment += "### Critical Issues\n"
            for issue in review_result["critical_issues"]:
                comment += f"- 🚨 {issue}\n"
            comment += "\n"
            
        if review_result["non_critical_issues"]:
            comment += "### Suggestions\n"
            for issue in review_result["non_critical_issues"]:
                comment += f"- 💡 {issue}\n"
            comment += "\n"
            
        if review_result["positive_feedback"]:
            comment += "### Positive Feedback\n"
            for feedback in review_result["positive_feedback"]:
                comment += f"- ✨ {feedback}\n"
            comment += "\n"
            
        if review_result["recommendations"]:
            comment += "### Recommendations\n"
            for rec in review_result["recommendations"]:
                comment += f"- 📝 {rec}\n"
                
        await self.github.add_pr_comment(pr_url, comment)
    
    async def handle_review_request(self, message: dict) -> dict:
        """Handle code review request"""
        review_result = await self.review_code(message["pr_url"])
        
        return {
            "status": "success",
            "approved": review_result["approved"],
            "comments": review_result["comments"]
        }
    
    async def break_down_story(self, story: dict) -> List[Task]:
        """Break down a user story into smaller technical tasks.
        
        Args:
            story: Dictionary containing story details
            
        Returns:
            List[Task]: List of tasks to implement the story
        """
        self.logger.info(f"Breaking down story: {story['title']}")
        
        prompt = f"""Break down this user story into tasks. For each task, provide a JSON object with these fields:
        - title: task title
        - description: detailed task description
        - type: one of [setup, implementation, testing]
        - complexity: number 1-5
        - dependencies: list of task titles this task depends on
        - required_skills: list of technical skills needed for this task
        - risk_factors: list of potential risks (e.g., performance, security, reliability)

        Story Title: {story['title']}
        Story Description: {story['description']}
        Focus: {self.focus}

        Return the tasks as a JSON array with format:
        {{"tasks": [
            {{"title": "...", "description": "...", "type": "...", "complexity": 1, "dependencies": [], "required_skills": [], "risk_factors": []}},
            ...
        ]}}
        """
        
        response = await self.generate_response(prompt)
        self.logger.debug(f"Raw LLM response:\n{response}")
        
        try:
            # Try to clean up the response if it's not pure JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response.split('```json')[1]
            if response.endswith('```'):
                response = response.rsplit('```', 1)[0]
            response = response.strip()
            
            tasks_data = json.loads(response)
            if not isinstance(tasks_data, dict) or "tasks" not in tasks_data:
                self.logger.error("LLM response is not a valid JSON object with tasks array")
                return []
                
            tasks = []
            for task_data in tasks_data["tasks"]:
                try:
                    task = Task(
                        id=str(uuid.uuid4()),
                        title=task_data["title"], 
                        description=task_data["description"],
                        requires_ux=self.focus == "frontend",
                        metadata={
                            "type": task_data["type"],
                            "complexity": task_data["complexity"],
                            "dependencies": task_data.get("dependencies", []),
                            "required_skills": task_data.get("required_skills", ["python"]),
                            "risk_factors": task_data.get("risk_factors", [])
                        }
                    )
                    tasks.append(task)
                except KeyError as e:
                    self.logger.error(f"Missing required field in task data: {e}")
                    self.logger.debug(f"Task data: {task_data}")
                    continue
                    
            if not tasks:
                self.logger.error("No valid tasks could be created from LLM response")
                
            # Validate the task breakdown
            self._validate_task_breakdown(tasks)
            
            return tasks
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response that failed to parse: {response}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error parsing tasks: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            return []
    
    def _parse_task_breakdown(self, response: str) -> List[Dict[str, Any]]:
        """Parse the task breakdown response into structured tasks."""
        tasks = []
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        self.logger.debug(f"Parsing task breakdown response:\n{response}")
        
        current_task = None
        task_content = []
        
        # First pass: Group lines that seem to belong to the same task
        for line in lines:
            # Skip section headers and empty lines
            if line.lower() in ('functional requirements:', 'technical requirements:', 'requirements:'):
                continue
                
            # If line starts with a number or dash, it's likely a new task
            if line.startswith(('-', '*')) or (line[0].isdigit() and line[1] in (')', '.', ':')):
                if task_content:
                    # Process previous task content
                    tasks.append(self._extract_task_info(task_content))
                task_content = [line.lstrip('-*0123456789.) :')]
            else:
                # Continue with current task
                task_content.append(line)
                
        # Don't forget the last task
        if task_content:
            tasks.append(self._extract_task_info(task_content))
            
        self.logger.debug(f"Parsed {len(tasks)} tasks")
        return tasks
        
    def _extract_task_info(self, content: List[str]) -> Dict[str, Any]:
        """Extract task information from a group of related lines."""
        # Join all lines to analyze the full content
        full_content = ' '.join(content)
        
        # Extract what appears to be the title (first sentence or phrase)
        title = content[0].split('.')[0].strip()
        
        # The rest is the description
        description = ' '.join(content[1:]) if len(content) > 1 else ''
        
        # Infer task type based on content keywords
        task_type = 'implementation'  # default
        if any(word in full_content.lower() for word in ['setup', 'initialize', 'configure', 'install']):
            task_type = 'setup'
        elif any(word in full_content.lower() for word in ['test', 'verify', 'validate', 'assert']):
            task_type = 'testing'
            
        # Infer complexity based on certain keywords
        complexity = 1  # default
        if any(word in full_content.lower() for word in ['complex', 'difficult', 'challenging']):
            complexity = 4
        elif any(word in full_content.lower() for word in ['moderate', 'medium']):
            complexity = 3
        elif any(word in full_content.lower() for word in ['simple', 'easy', 'basic']):
            complexity = 1
            
        # Extract skills from content
        skills = set()
        common_skills = ['python', 'fastapi', 'api', 'rest', 'database', 'sql', 'testing', 'pytest']
        for skill in common_skills:
            if skill in full_content.lower():
                skills.add(skill)
                
        # Identify risk factors
        risks = []
        risk_keywords = ['error', 'fail', 'timeout', 'crash', 'performance', 'security']
        for keyword in risk_keywords:
            if keyword in full_content.lower():
                risks.append(f"{keyword} risk")
                
        return {
            'id': str(uuid.uuid4()),
            'title': title,
            'description': description or full_content,  # fallback to full content if no separate description
            'dependencies': [],  # Dependencies will be inferred by task order
            'complexity': complexity,
            'required_skills': list(skills),
            'type': task_type,
            'risk_factors': risks
        }
        
    def _build_task_graph(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a graph representation of task dependencies."""
        graph = {
            'nodes': {},
            'edges': [],
            'entry_points': [],
            'exit_points': []
        }
        
        # Create nodes
        for task in tasks:
            graph['nodes'][task['id']] = task
            
        # Create edges from dependencies
        for task in tasks:
            if not task['dependencies']:
                graph['entry_points'].append(task['id'])
            has_dependents = False
            for other_task in tasks:
                if task['title'] in other_task['dependencies']:
                    graph['edges'].append({
                        'from': task['id'],
                        'to': other_task['id'],
                        'weight': other_task['complexity']
                    })
                    has_dependents = True
            if not has_dependents:
                graph['exit_points'].append(task['id'])
                
        return graph
        
    def _optimize_task_order(self, graph: Dict[str, Any]) -> List[Task]:
        """Optimize task order based on dependencies and complexity."""
        ordered_tasks = []
        visited = set()
        
        def visit(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)
            
            # Visit dependencies first
            for edge in graph['edges']:
                if edge['to'] == task_id:
                    visit(edge['from'])
                    
            # Add task to ordered list
            task_data = graph['nodes'][task_id]
            ordered_tasks.append(Task(
                id=task_data['id'],
                title=task_data['title'],
                description=task_data['description'],
                requires_ux=self.focus == "frontend" or "ux" in task_data['required_skills'],
                metadata={
                    'complexity': task_data['complexity'],
                    'required_skills': task_data['required_skills'],
                    'type': task_data['type'],
                    'risk_factors': task_data['risk_factors']
                }
            ))
            
        # Start with entry points
        for entry_point in graph['entry_points']:
            visit(entry_point)
            
        return ordered_tasks
        
    def _validate_task_breakdown(self, tasks: List[Task]):
        """Validate the task breakdown for completeness and consistency."""
        if not tasks:
            self.logger.error("No tasks found in breakdown")
            raise ValueError("Task breakdown validation failed: No tasks found")
            
        # Check for minimum required tasks
        if not any(t.metadata['type'] == 'setup' for t in tasks):
            self.logger.warning("No setup tasks found in breakdown")
            
        if not any(t.metadata['type'] == 'testing' for t in tasks):
            self.logger.warning("No testing tasks found in breakdown")
            
        # Check complexity distribution
        complexities = [t.metadata['complexity'] for t in tasks]
        avg_complexity = sum(complexities) / len(complexities)  # Safe now because we check for empty list above
        if avg_complexity > 3:
            self.logger.warning(f"High average task complexity: {avg_complexity}")
            
        # Check for balanced skill requirements
        all_skills = set()
        for task in tasks:
            all_skills.update(task.metadata['required_skills'])
            
        if len(all_skills) < 2:
            self.logger.warning("Limited skill requirements in task breakdown")
            
        # Check risk distribution
        high_risk_tasks = [t for t in tasks if len(t.metadata['risk_factors']) > 2]
        if len(high_risk_tasks) > len(tasks) / 3:
            self.logger.warning("High proportion of risky tasks")
    
    def needs_ux_design(self, tasks: List[Task]) -> bool:
        """Determine if any tasks require UX design."""
        return any(task.requires_ux for task in tasks)
    
    def _integrate_feedback(self, feedback: Dict[str, Any]) -> None:
        """Integrate feedback into the agent's knowledge base.
        
        Args:
            feedback: Dictionary containing feedback details including:
                     - type (review/implementation)
                     - content (the actual feedback)
                     - context (code or PR context)
                     - outcome (success/failure)
        """
        self.feedback_history.append(feedback)
        
    def _get_relevant_feedback(self, context: str) -> List[Dict[str, Any]]:
        """Retrieve relevant feedback based on current context.
        
        Args:
            context: The current development context (e.g., task description, code)
            
        Returns:
            List[Dict[str, Any]]: List of relevant feedback entries
        """
        # Generate embeddings for context and feedback entries
        context_embedding = self.generate_embedding(context)
        
        relevant_feedback = []
        for entry in self.feedback_history:
            entry_embedding = self.generate_embedding(entry["context"])
            similarity = self._calculate_similarity(context_embedding, entry_embedding)
            
            if similarity > 0.8:  # Threshold for relevance
                relevant_feedback.append(entry)
                
        return sorted(relevant_feedback, key=lambda x: x.get("timestamp", 0), reverse=True)[:5]
        
    async def implement_task(self, task: Task) -> dict:
        """Implement a development task."""
        self.logger.info(f"Implementing task: {task.title}")
        
        # Determine file path based on task type
        file_path = self._determine_file_path(task)
        
        # Get implementation context
        context = self._gather_implementation_context(task, file_path)
        
        # Generate implementation prompt
        prompt = f"""Implement code for this task:
        Title: {task.title}
        Description: {task.description}
        
        Context:
        {context}
        
        Requirements:
        - Follow best practices and patterns
        - Include error handling
        - Add comments explaining complex logic
        - Add type hints
        - Include unit tests
        
        Return only the implementation code.
        """
        
        code = await self.generate_response(prompt)
        
        # Validate implementation
        validation_result = await self._validate_implementation(code, task)
        if not validation_result["valid"]:
            self.logger.warning(f"Implementation failed validation: {validation_result['reasons']}")
            
            # Store feedback about the failed attempt
            self._integrate_feedback({
                "type": "implementation",
                "content": validation_result["reasons"],
                "context": task.description,
                "outcome": "failure",
                "timestamp": time.time()
            })
            
            # Try one more time with validation feedback
            prompt += f"\nPrevious attempt failed validation:\n{validation_result['reasons']}\nPlease fix these issues."
            code = await self.generate_response(prompt)
            
            # Validate again
            validation_result = await self._validate_implementation(code, task)
            if not validation_result["valid"]:
                raise ValueError(f"Implementation failed validation: {validation_result['reasons']}")
                
        # Store feedback about the successful implementation
        self._integrate_feedback({
            "type": "implementation",
            "content": "Implementation successful",
            "context": task.description,
            "code": code,
            "outcome": "success",
            "timestamp": time.time()
        })
        
        return {
            "code": code,
            "file_path": file_path,
            "validation": validation_result
        }
        
    def _format_feedback_for_prompt(self, feedback: List[Dict[str, Any]]) -> str:
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
                formatted.append(f"Previous Success Pattern:\n{entry.get('code', 'No code available')}")
            else:
                formatted.append(f"Previous Issues to Avoid:\n{entry['content']}")
                
        return "\n\n".join(formatted)
        
    def _determine_file_path(self, task: Task) -> str:
        """Determine the appropriate file path for a task."""
        title_lower = task.title.lower()
        
        if "model" in title_lower or "database" in title_lower:
            return "src/models/model.py"
        elif "endpoint" in title_lower or "api" in title_lower:
            return "src/api/routes.py"
        elif "component" in title_lower or "ui" in title_lower:
            return "src/ui/components.py"
        elif "test" in title_lower:
            return "tests/test_main.py"
        else:
            # Create a valid Python module name
            module_name = "_".join(word.lower() for word in task.title.split() if word.isalnum())
            return f"src/core/{module_name}.py"
            
    def _gather_implementation_context(self, task: Task, file_path: str) -> str:
        """Gather context for implementation including existing code and dependencies."""
        context_parts = []
        
        # Add existing file content if it exists
        try:
            with open(file_path, 'r') as f:
                existing_code = f.read()
                context_parts.append(f"Existing file content:\n{existing_code}")
        except FileNotFoundError:
            context_parts.append("This will be a new file.")
            
        # Add related files based on task type
        if "model" in task.title.lower():
            context_parts.append("This should follow the existing model patterns.")
        elif "api" in task.title.lower():
            context_parts.append("This should follow REST API best practices.")
            
        return "\n".join(context_parts)
        
    async def _validate_implementation(self, code: str, task: Task) -> dict:
        """Validate implementation against quality standards."""
        validation_prompt = f"""Validate this implementation against these criteria:
        Code:
        {code}
        
        Validation criteria:
        1. Proper type hints
        2. Comprehensive docstrings
        3. Error handling
        4. Input validation
        5. Edge case handling
        6. SOLID principles
        7. Testability
        8. Logging
        
        Respond with:
        - valid: true/false
        - reasons: list of validation failures
        """
        
        validation_response = await self.generate_response(validation_prompt)
        
        # Parse validation response
        valid = "valid: true" in validation_response.lower()
        reasons = []
        
        if not valid:
            # Extract reasons between "reasons:" and the next section or end
            reasons_text = validation_response.split("reasons:")[1].split("\n")
            reasons = [r.strip("- ").strip() for r in reasons_text if r.strip()]
            
        return {
            "valid": valid,
            "reasons": reasons
        }
        
    async def implement_tasks(self, tasks: List[Task]) -> dict:
        """Implement multiple technical tasks with quality controls."""
        self.logger.info(f"Implementing {len(tasks)} tasks")
        
        implementations = {}
        failed_tasks = []
        
        for task in tasks:
            try:
                implementation = await self.implement_task(task)
                implementations[task.id] = {
                    "code": implementation["code"],
                    "task": task.dict(),
                    "validation": implementation["validation"]
                }
            except Exception as e:
                self.logger.error(f"Failed to implement task {task.id}: {str(e)}")
                failed_tasks.append({
                    "task_id": task.id,
                    "error": str(e)
                })
                
        if failed_tasks:
            self.logger.warning(f"Failed to implement {len(failed_tasks)} tasks")
            
        return {
            "implementations": implementations,
            "failed_tasks": failed_tasks
        }
    
    async def create_pr(self, implementation_result: dict) -> str:
        """Create a pull request with the implemented changes."""
        self.logger.info("Creating pull request")
        
        # Validate implementations in isolated environment
        validation_results = await self._validate_implementations(implementation_result)
        
        if not validation_results["valid"]:
            raise ValueError(
                f"Implementation validation failed:\n{validation_results['error']}\n"
                f"Logs:\n{validation_results.get('logs', 'No logs available')}"
            )
        
        # Prepare PR description with validation results
        pr_description = "## Implementation Details\n\n"
        for task_id, details in implementation_result["implementations"].items():
            pr_description += f"### {details['task']['title']}\n"
            pr_description += f"{details['task']['description']}\n\n"
            pr_description += "```python\n"
            pr_description += details['code']
            pr_description += "\n```\n\n"
            
        # Add validation results
        pr_description += "## Validation Results\n\n"
        pr_description += "✅ All implementations passed validation checks\n\n"
        pr_description += "### Details\n"
        pr_description += "- Startup check: Passed\n"
        pr_description += "- Health check: Passed\n"
        pr_description += f"- Container logs: {validation_results.get('logs', 'No logs available')}\n"
        
        # Create PR using GitHub service
        pr_url = await self.github.create_pull_request(
            repo_name="ai-dev-team",
            title=f"{self.focus}: Implement new features",
            body=pr_description
        )
        
        return pr_url
        
    async def _validate_implementations(self, implementation_result: dict) -> Dict[str, Any]:
        """Validate implementations in isolated environment."""
        from ..utils.validation_env import ValidationEnvironment
        
        # Extract all code files
        code_files = {}
        for task_id, details in implementation_result["implementations"].items():
            code_files[details["file_path"]] = details["code"]
            
        # Determine tech stack and entry point
        tech_stack = self._determine_tech_stack(code_files)
        entry_point = self._determine_entry_point(code_files)
        dependencies = self._extract_dependencies(code_files)
        
        # Create validation environment
        validation_env = ValidationEnvironment()
        try:
            await validation_env.setup(tech_stack, dependencies)
            return await validation_env.validate_implementation(
                code_files,
                tech_stack,
                entry_point
            )
        finally:
            await validation_env.cleanup()
            
    def _determine_tech_stack(self, code_files: Dict[str, str]) -> str:
        """Determine the technology stack from code files."""
        # Check for Python files
        if any(f.endswith('.py') for f in code_files):
            return "python"
        # Check for Node.js files
        elif any(f.endswith('.js') or f.endswith('.ts') for f in code_files):
            return "node"
        # Check for Java files
        elif any(f.endswith('.java') for f in code_files):
            return "java"
        else:
            return "python"  # Default to Python
            
    def _determine_entry_point(self, code_files: Dict[str, str]) -> str:
        """Determine the entry point file."""
        # Look for main.py or app.py for Python
        if "src/main.py" in code_files:
            return "src/main.py"
        elif "src/app.py" in code_files:
            return "src/app.py"
        # Look for index.js for Node
        elif "src/index.js" in code_files:
            return "src/index.js"
        else:
            # Use the first file as entry point
            return list(code_files.keys())[0]
            
    def _extract_dependencies(self, code_files: Dict[str, str]) -> Dict[str, str]:
        """Extract dependencies from code files."""
        dependencies = {}
        
        # Look for import statements in Python files
        for file_path, content in code_files.items():
            if file_path.endswith('.py'):
                for line in content.split('\n'):
                    if line.startswith('import ') or line.startswith('from '):
                        package = line.split()[1].split('.')[0]
                        if not package.startswith('.'):  # Ignore relative imports
                            dependencies[package] = "*"  # Use latest version
                            
        # Add essential packages
        dependencies.update({
            "fastapi": "0.104.1",
            "uvicorn": "0.24.0",
            "pydantic": "2.5.2"
        })
        
        return dependencies