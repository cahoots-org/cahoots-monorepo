from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import base64
from urllib.parse import urljoin
import logging
import asyncio
import uuid
from datetime import datetime, timezone

from app.api.dependencies import get_current_user
from app.models.task import Task
from typing import Dict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jira", tags=["jira"])
security = HTTPBearer()


@router.get("/status")
async def jira_connection_status():
    """Check if the user has JIRA configured."""
    # For now, just return not connected
    return {"connected": False}

class JiraCredentials(BaseModel):
    jira_url: str
    user_email: str
    api_token: str
    account_id: str

class JiraUser(BaseModel):
    username: str
    email: str

class JiraConfig(BaseModel):
    jira_url: str = Field(..., description="JIRA instance URL")
    user_email: str = Field(..., description="User's email for JIRA authentication")
    api_token: str = Field(..., description="JIRA API token")
    account_id: Optional[str] = Field(None, description="User's Atlassian account ID")
    project_name: str = Field(..., description="Name of the project to create")
    project_key: str = Field(..., description="Project key (short identifier)")
    users: List[JiraUser] = Field(default=[], description="Project users")

class TaskNode(BaseModel):
    task_id: str
    description: str
    status: str
    is_atomic: Optional[bool] = False
    story_points: Optional[int] = None
    implementation_details: Optional[str] = None
    depth: Optional[int] = 0
    parent_id: Optional[str] = None
    children: List['TaskNode'] = []

class JiraExportRequest(BaseModel):
    config: JiraConfig
    task_tree: TaskNode

# Update forward reference
TaskNode.model_rebuild()

class JiraApiClient:
    def __init__(self, jira_url: str, email: str, api_token: str):
        # Clean and validate the JIRA URL
        self.jira_url = jira_url.rstrip('/')

        # Ensure the URL has a scheme
        if not self.jira_url.startswith(('http://', 'https://')):
            self.jira_url = f'https://{self.jira_url}'

        # For Atlassian cloud instances, ensure we're using the correct format
        if '.atlassian.net' in self.jira_url and not self.jira_url.startswith('https://'):
            self.jira_url = self.jira_url.replace('http://', 'https://')

        logger.info(f"Initialized JIRA client with URL: {self.jira_url}")

        self.email = email
        self.api_token = api_token
        self.auth_header = base64.b64encode(f"{email}:{api_token}".encode()).decode()

    async def make_request(self, endpoint: str, method: str = "GET", data: Dict[Any, Any] = None, retry_count: int = 3) -> Dict[Any, Any]:
        """Make authenticated request to JIRA API with retry logic"""
        url = urljoin(f"{self.jira_url}/", f"rest/api/3{endpoint}")

        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        last_error = None
        for attempt in range(retry_count):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=headers)
                    elif method.upper() == "POST":
                        response = await client.post(url, headers=headers, json=data)
                    elif method.upper() == "PUT":
                        response = await client.put(url, headers=headers, json=data)
                    else:
                        raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")

                if response.status_code == 401:
                    error_text = response.text
                    logger.error(f"JIRA 401 error: {error_text}")
                    raise HTTPException(status_code=401, detail="JIRA authentication failed. Check your email and API token.")
                elif response.status_code == 403:
                    error_text = response.text
                    logger.error(f"JIRA 403 error for {url}: {error_text}")
                    # Parse error to provide more detail
                    try:
                        error_json = response.json()
                        error_messages = error_json.get("errorMessages", [])
                        if error_messages:
                            detail = f"JIRA Permission Error: {'; '.join(error_messages)}"
                        else:
                            detail = f"JIRA Permission Error: {error_text}"
                    except:
                        detail = f"Insufficient permissions for this JIRA operation. Response: {error_text}"
                    raise HTTPException(status_code=403, detail=detail)
                elif response.status_code == 500:
                    error_text = response.text
                    logger.warning(f"JIRA 500 error for {url} (attempt {attempt + 1}/{retry_count}): {error_text}")

                    if attempt < retry_count - 1:
                        # Wait before retrying (exponential backoff)
                        import asyncio
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue

                    # Final attempt failed
                    if "/project" in url and method == "POST":
                        detail = "JIRA server error creating project. Many JIRA instances don't allow API project creation. Please create the project manually in JIRA first."
                    else:
                        detail = f"JIRA server error after {retry_count} attempts: {error_text}"
                    raise HTTPException(status_code=500, detail=detail)
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = response.headers.get('Retry-After', 5)
                    logger.warning(f"Rate limited, waiting {retry_after} seconds...")

                    if attempt < retry_count - 1:
                        import asyncio
                        await asyncio.sleep(int(retry_after))
                        continue

                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                elif response.status_code >= 400:
                    error_text = response.text
                    logger.error(f"JIRA {response.status_code} error: {error_text}")
                    raise HTTPException(status_code=response.status_code, detail=f"JIRA API Error: {error_text}")

                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < retry_count - 1:
                    logger.warning(f"Request timeout (attempt {attempt + 1}/{retry_count}), retrying...")
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise HTTPException(status_code=408, detail="JIRA API request timed out after retries")
            except httpx.RequestError as e:
                last_error = e
                error_msg = str(e)

                # Don't retry for certain errors
                if "No address associated with hostname" in error_msg or "Name or service not known" in error_msg:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot connect to JIRA URL '{self.jira_url}'. Please check that the URL is correct and accessible."
                    )
                elif "SSL" in error_msg or "certificate" in error_msg.lower():
                    raise HTTPException(
                        status_code=400,
                        detail=f"SSL/Certificate error connecting to JIRA. If using a self-signed certificate, additional configuration may be needed."
                    )

                # Retry for other network errors
                if attempt < retry_count - 1:
                    logger.warning(f"Network error (attempt {attempt + 1}/{retry_count}): {error_msg}, retrying...")
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue

                raise HTTPException(status_code=500, detail=f"Network error connecting to JIRA after {retry_count} attempts: {error_msg}")

        # If we get here, all retries failed
        if last_error:
            raise HTTPException(status_code=500, detail=f"All retry attempts failed: {str(last_error)}")


    async def create_project(self, project_data: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """Create JIRA project"""
        # First check if project already exists
        try:
            existing_project = await self.make_request(f"/project/{project_data['key']}")
            logger.info(f"Project {project_data['key']} already exists")
            return existing_project
        except HTTPException as e:
            if e.status_code != 404:
                # Unexpected error checking for project
                logger.error(f"Error checking for existing project: {e.detail}")
                raise
            # Project doesn't exist (404), continue to create it
            logger.info(f"Project {project_data['key']} does not exist, will create it")

        try:
            # Set user account ID for project lead
            if not project_data.get("leadAccountId"):
                project_data["leadAccountId"] = account_id

            logger.info(f"Creating JIRA project with data: {project_data}")
            result = await self.make_request("/project", "POST", project_data)
            logger.info(f"Successfully created project: {result}")
            return result
        except HTTPException as e:
            logger.error(f"Failed to create project: status={e.status_code}, detail={e.detail}")

            if e.status_code == 400:
                # Bad request - check if it's because project exists
                try:
                    return await self.make_request(f"/project/{project_data['key']}")
                except:
                    pass

                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to create project '{project_data['key']}'. The project key may already be taken or invalid. Error: {e.detail}"
                )
            elif e.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied. Your API token needs 'Administer Jira' permission to create projects. Please create the project '{project_data['key']}' manually in JIRA first."
                )
            elif e.status_code == 500:
                raise HTTPException(
                    status_code=500,
                    detail=f"JIRA server error when creating project. This often means you need to create the project manually. Please create project '{project_data['key']}' in JIRA and try again."
                )
            raise

    async def get_project_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """Get available issue types for a project"""
        try:
            project_data = await self.make_request(f"/project/{project_key}")
            return project_data.get("issueTypes", [])
        except Exception as e:
            logger.error(f"Failed to get issue types for project {project_key}: {e}")
            return []

    async def get_valid_issue_type(self, project_key: str, preferred_type: str = "Task") -> str:
        """Get a valid issue type for the project, preferring the specified type"""
        issue_types = await self.get_project_issue_types(project_key)
        
        if not issue_types:
            logger.warning(f"No issue types found for project {project_key}, using default")
            return "Task"
        
        # Log available issue types for debugging
        type_names = [it.get("name") for it in issue_types]
        logger.info(f"Available issue types for {project_key}: {type_names}")
        
        # Check if preferred type exists
        for issue_type in issue_types:
            if issue_type.get("name") == preferred_type:
                return preferred_type
        
        # Fallback hierarchy: Task -> Bug -> Story -> first available
        fallback_types = ["Task", "Bug", "Story"]
        for fallback in fallback_types:
            for issue_type in issue_types:
                if issue_type.get("name") == fallback:
                    logger.info(f"Using fallback issue type: {fallback}")
                    return fallback
        
        # Use first available type
        first_type = issue_types[0].get("name", "Task")
        logger.info(f"Using first available issue type: {first_type}")
        return first_type

    async def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create JIRA issue"""
        try:
            return await self.make_request("/issue", "POST", issue_data)
        except HTTPException as e:
            # Log the full error for debugging
            logger.error(f"JIRA issue creation failed. Payload: {issue_data}")
            logger.error(f"JIRA error response: {e.detail}")
            raise

    async def update_issue_labels(self, issue_key: str, labels: List[str]) -> Dict[str, Any]:
        """Update JIRA issue labels"""
        try:
            update_data = {
                "fields": {
                    "labels": labels
                }
            }
            return await self.make_request(f"/issue/{issue_key}", "PUT", update_data)
        except HTTPException as e:
            logger.warning(f"Failed to update labels for issue {issue_key}: {e.detail}")
            # Don't fail the entire export if labels can't be updated
            return {"warning": f"Labels not updated for {issue_key}"}

@router.post("/credentials")
async def save_jira_credentials(
    credentials: JiraCredentials,
    current_user: dict = Depends(get_current_user)
):
    """Save JIRA API credentials for the current user."""
    # Since we're not persisting in this version, just return success
    # In a real implementation, you would save these to a database
    return {
        "message": "JIRA credentials saved successfully",
        "jira_url": credentials.jira_url,
        "user_email": credentials.user_email,
        "account_id": credentials.account_id,
        "api_token": "*****"  # Don't return the actual token for security
    }

@router.get("/credentials")
async def get_jira_credentials(current_user: dict = Depends(get_current_user)):
    """Get JIRA API credentials for the current user."""
    # In a real implementation, you would fetch this from the database
    # For now, just return no credentials
    return {
        "has_credentials": False,
        "jira_url": None,
        "user_email": None,
        "account_id": None
    }

@router.post("/start-export")
async def start_jira_export(
    request: JiraExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start JIRA export and return export ID for WebSocket connection"""
    # Generate export ID
    export_id = f"jira_export_{request.config.project_key}_{uuid.uuid4().hex[:8]}"
    
    # Start export in background
    asyncio.create_task(perform_jira_export(export_id, request, current_user))
    
    return {
        "export_id": export_id,
        "message": "Export started, connect to WebSocket for progress updates"
    }

async def perform_jira_export(export_id: str, request: JiraExportRequest, current_user: dict):
    """Perform the actual JIRA export with progress updates"""
    logger.info(f"Starting JIRA export {export_id}")
    logger.info(f"Request config: project_key={request.config.project_key}, project_name={request.config.project_name}")

    try:
        # Use credentials from request (no persistence in this version)
        jira_url = request.config.jira_url
        user_email = request.config.user_email
        api_token = request.config.api_token
        account_id = request.config.account_id

        logger.info(f"JIRA credentials: url={jira_url}, email={user_email}, has_token={bool(api_token)}, account_id={account_id}")

        if not all([jira_url, user_email, api_token, account_id]):
            raise HTTPException(
                status_code=400,
                detail="JIRA credentials not found. Please configure JIRA integration in Settings including your Atlassian Account ID."
            )

        # Validate JIRA URL format
        if not jira_url or jira_url.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="JIRA URL is required. Please provide your JIRA instance URL (e.g., 'yourcompany.atlassian.net')"
            )
        
        async def send_progress(step: str, progress: int, message: str):
            """Send progress update via WebSocket"""
            try:
                from app.websocket.manager import websocket_manager

                # Send to WebSocket clients connected to this export
                await websocket_manager.broadcast_to_task(
                    export_id,
                    {
                        "type": "jira.export.progress",
                        "payload": {
                            "export_id": export_id,
                            "step": step,
                            "progress": progress,
                            "message": message,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                logger.info(f"Sent progress update for export {export_id}: {progress}% - {message}")
            except Exception as e:
                logger.warning(f"Failed to send progress update: {e}")

        # Initialize JIRA client
        jira_client = JiraApiClient(jira_url, user_email, api_token)

        # Test authentication first
        try:
            await send_progress("authentication", 2, "Connecting to JIRA...")
            myself_response = await jira_client.make_request("/myself")
            account_id = myself_response.get('accountId', account_id)
            logger.info(f"JIRA authentication successful for user: {myself_response.get('displayName', user_email)}")
            await send_progress("authentication", 5, "Authentication successful")
        except HTTPException as e:
            if e.status_code == 400 and "Cannot connect to JIRA URL" in e.detail:
                # URL connection issue
                await send_progress("error", 0, e.detail)
                raise
            elif e.status_code == 401:
                # Authentication failure
                error_msg = "JIRA authentication failed. Please check your email and API token."
                await send_progress("error", 0, error_msg)
                raise HTTPException(status_code=401, detail=error_msg)
            else:
                raise

        # Step 1: Create project (5% to 20%)
        await send_progress("project_creation", 5, "Creating JIRA project...")
        project_data = {
            "key": request.config.project_key,
            "name": request.config.project_name,
            "projectTypeKey": "software",
            "description": "Project exported from Cahoots Task Manager"
        }

        project = await jira_client.create_project(project_data, account_id)
        await send_progress("project_creation", 20, f"Project '{project['key']}' ready")

        # Step 2: Create issues from task tree
        created_issues = {}
        
        def format_label(text: str) -> str:
            """Format text as a JIRA label: first 15 chars, lowercase, spaces to dashes"""
            if not text:
                return ""
            # Take first 15 chars, convert to lowercase, replace spaces with dashes
            label = text[:15].lower().replace(' ', '-')
            # Remove any characters that aren't alphanumeric or dashes
            label = ''.join(c for c in label if c.isalnum() or c == '-')
            return label

        def collect_parent_labels(node: TaskNode, all_nodes: Dict[str, TaskNode], labels: List[str] = None) -> List[str]:
            """Recursively collect parent task labels"""
            if labels is None:
                labels = []
            
            if node.parent_id and node.parent_id in all_nodes:
                parent = all_nodes[node.parent_id]
                parent_label = format_label(parent.description)
                if parent_label:
                    labels.append(parent_label)
                # Recursively collect grandparent labels
                collect_parent_labels(parent, all_nodes, labels)
            
            return labels

        # Count total atomic tasks for progress tracking
        def count_atomic_tasks(node: TaskNode) -> int:
            """Count total atomic tasks in the tree"""
            count = 1 if node.is_atomic else 0
            if node.children:
                for child in node.children:
                    count += count_atomic_tasks(child)
            return count

        total_atomic_tasks = count_atomic_tasks(request.task_tree)
        created_count = 0

        async def process_node(node: TaskNode, all_nodes: Dict[str, TaskNode], parent_labels: List[str] = None):
            """Process task tree nodes - only create JIRA issues for atomic tasks"""
            nonlocal created_count
            
            # Only create JIRA issues for atomic tasks
            if node.is_atomic:
                # Collect all parent labels for this atomic task
                labels = collect_parent_labels(node, all_nodes)
                
                progress_percent = 20 + int((created_count / total_atomic_tasks) * 60)  # 20% to 80%
                await send_progress("issue_creation", progress_percent, 
                                  f"Creating issue {created_count + 1}/{total_atomic_tasks}: {node.description[:50]}...")
                
                # Build description in Atlassian Document Format (ADF)
                # Use implementation details as the main description
                description_content = []
                
                # Main description from implementation details
                if node.implementation_details:
                    description_content.append({
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": node.implementation_details
                            }
                        ]
                    })
                
                # Add task description as context if different from implementation details
                if node.description and node.description != node.implementation_details:
                    description_content.extend([
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Task Context:",
                                    "marks": [{"type": "strong"}]
                                }
                            ]
                        },
                        {
                            "type": "paragraph", 
                            "content": [
                                {
                                    "type": "text",
                                    "text": node.description
                                }
                            ]
                        }
                    ])

                # Convert to Atlassian Document Format
                description_adf = {
                    "type": "doc",
                    "version": 1,
                    "content": description_content if description_content else [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "No implementation details provided"
                                }
                            ]
                        }
                    ]
                }

                # Map priority based on story points
                priority = "Medium"
                if node.story_points:
                    if node.story_points <= 1:
                        priority = "Lowest"
                    elif node.story_points <= 3:
                        priority = "Low"
                    elif node.story_points <= 5:
                        priority = "Medium"
                    elif node.story_points <= 8:
                        priority = "High"
                    else:
                        priority = "Highest"

                # Create issue payload
                issue_payload = {
                    "fields": {
                        "project": {"key": request.config.project_key},
                        "summary": (node.description or "Untitled Task").split('\n')[0][:255],
                        "description": description_adf,
                        "issuetype": {"name": await jira_client.get_valid_issue_type(request.config.project_key, "Task")},
                        "priority": {"name": priority}
                    }
                }

                # Create the issue (without labels for now)
                logger.info(f"Creating atomic task: {node.description[:50]}...")
                logger.debug(f"Issue payload: {issue_payload}")
                created_issue = await jira_client.create_issue(issue_payload)
                issue_key = created_issue["key"]
                created_issues[node.task_id] = issue_key
                
                # Store labels for batch update later
                if labels:
                    if not hasattr(process_node, 'issues_to_label'):
                        process_node.issues_to_label = []
                    process_node.issues_to_label.append((issue_key, labels))
                
                created_count += 1

            # Process children regardless of whether we created an issue for this node
            if node.children:
                for child in node.children:
                    await process_node(child, all_nodes)

        # Build a dictionary of all nodes for efficient parent lookup
        def build_all_nodes(node: TaskNode, all_nodes: Dict[str, TaskNode] = None) -> Dict[str, TaskNode]:
            """Recursively build dictionary of all nodes in the tree"""
            if all_nodes is None:
                all_nodes = {}
            
            all_nodes[node.task_id] = node
            
            if node.children:
                for child in node.children:
                    build_all_nodes(child, all_nodes)
            
            return all_nodes

        # Build the all_nodes dictionary
        all_nodes = build_all_nodes(request.task_tree)

        # Initialize the issues_to_label list
        process_node.issues_to_label = []

        # Process task tree
        if request.task_tree.children:
            for child in request.task_tree.children:
                await process_node(child, all_nodes)
        else:
            # If no children, process root task
            await process_node(request.task_tree, all_nodes)

        # Step 3: Batch update labels for all created issues (80% to 95%)
        if hasattr(process_node, 'issues_to_label') and process_node.issues_to_label:
            await send_progress("label_update", 80, f"Starting label updates for {len(process_node.issues_to_label)} issues...")
            logger.info(f"Updating labels for {len(process_node.issues_to_label)} issues...")
            
            # Process labels in batches for better performance
            batch_size = 5
            total_batches = (len(process_node.issues_to_label) + batch_size - 1) // batch_size
            
            for batch_idx, i in enumerate(range(0, len(process_node.issues_to_label), batch_size)):
                batch = process_node.issues_to_label[i:i + batch_size]
                
                progress_percent = 80 + int((batch_idx / total_batches) * 15)  # 80% to 95%
                batch_issues = [issue_key for issue_key, _ in batch]
                await send_progress("label_update", progress_percent, 
                                  f"Updating labels for issues: {', '.join(batch_issues)}")
                
                # Create tasks for concurrent label updates
                update_tasks = []
                for issue_key, labels in batch:
                    logger.info(f"Adding labels {labels} to issue {issue_key}")
                    update_tasks.append(jira_client.update_issue_labels(issue_key, labels))
                
                # Execute batch concurrently
                await asyncio.gather(*update_tasks, return_exceptions=True)

        # Prepare completion message
        failed_count = len(process_node.failed_issues) if hasattr(process_node, 'failed_issues') else 0
        if failed_count > 0:
            completion_msg = f"Export completed with partial success. Created {len(created_issues)} issues, {failed_count} failed."
        else:
            completion_msg = f"Export completed successfully! Created {len(created_issues)} issues in JIRA project {project['key']}."

        await send_progress("completion", 100, completion_msg)
        
        # Send completion message with full result data
        failed_count = len(process_node.failed_issues) if hasattr(process_node, 'failed_issues') else 0

        try:
            from app.websocket.manager import websocket_manager
            result_data = {
                "success": failed_count == 0,
                "partial_success": failed_count > 0 and len(created_issues) > 0,
                "export_id": export_id,
                "project_key": project["key"],
                "project_url": f"{request.config.jira_url}/browse/{project['key']}",
                "issues_created": len(created_issues),
                "issues_failed": failed_count,
                "created_issues": created_issues
            }

            if failed_count > 0:
                result_data["failed_tasks"] = process_node.failed_issues[:10]  # Include first 10 failures

            await websocket_manager.broadcast_to_task(
                export_id,
                {
                    "type": "jira.export.success" if failed_count == 0 else "jira.export.partial_success",
                    "payload": result_data
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send completion message: {e}")

        if failed_count > 0:
            logger.info(f"JIRA export completed with {len(created_issues)} successful and {failed_count} failed issues")
        else:
            logger.info(f"Successfully created {len(created_issues)} issues in JIRA project {request.config.project_key}")

        result = {
            "success": failed_count == 0,
            "partial_success": failed_count > 0 and len(created_issues) > 0,
            "export_id": export_id,
            "project_key": project["key"],
            "project_url": f"{request.config.jira_url}/browse/{project['key']}",
            "issues_created": len(created_issues),
            "issues_failed": failed_count,
            "created_issues": created_issues
        }

        if failed_count > 0:
            result["failed_tasks"] = process_node.failed_issues[:10]  # Include first 10 failures

        return result

    except Exception as e:
        import traceback
        logger.error(f"Unexpected error during JIRA export: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Send error message via WebSocket
        try:
            from app.websocket.manager import websocket_manager
            await websocket_manager.broadcast_to_task(
                export_id,
                {
                    "type": "jira.export.error",
                    "payload": {
                        "message": str(e),
                        "export_id": export_id
                    }
                }
            )
        except Exception as ws_error:
            logger.error(f"Failed to send error via WebSocket: {ws_error}")

@router.post("/export")
async def export_to_jira(
    request: JiraExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Legacy export endpoint - redirects to new start-export"""
    return await start_jira_export(request, current_user)

@router.get("/test-connection")
async def test_jira_connection(
    jira_url: str,
    email: str, 
    api_token: str,
    current_user: dict = Depends(get_current_user)
):
    """Test JIRA connection with provided credentials"""
    try:
        jira_client = JiraApiClient(jira_url, email, api_token)
        
        # Test connection by making a simple API call
        test_response = await jira_client.make_request("/serverInfo")
        
        return {
            "success": True,
            "message": "Connection successful",
            "email": email,
            "server_info": test_response.get("serverTitle", "JIRA")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")