from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Optional
import httpx
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.models.task import Task

router = APIRouter(prefix="/api/trello", tags=["trello"])
logger = logging.getLogger(__name__)

TRELLO_API_BASE_URL = "https://api.trello.com/1"


@router.get("/status")
async def trello_connection_status():
    """Check if the user has Trello configured."""
    # For now, just return not connected
    return {"connected": False}

class TrelloCredentials(BaseModel):
    api_key: str
    token: str

class TrelloBoardCreate(BaseModel):
    name: str
    task_id: str
    api_key: Optional[str] = None
    token: Optional[str] = None

class TrelloExportResponse(BaseModel):
    board_url: str
    board_id: str

class TrelloConfig(BaseModel):
    trello_api_key: str
    trello_token: str
    board_name: str

class TaskNode(BaseModel):
    task_id: str
    description: str
    status: str
    is_atomic: Optional[bool] = False
    story_points: Optional[int] = None
    implementation_details: Optional[str] = None
    depth: Optional[int] = 0
    parent_id: Optional[str] = None
    children: Optional[List['TaskNode']] = None

class TrelloStartExportRequest(BaseModel):
    config: TrelloConfig
    task_tree: TaskNode

# Update forward reference
TaskNode.model_rebuild()

@router.post("/credentials")
async def save_trello_credentials(
    credentials: TrelloCredentials,
    current_user: dict = Depends(get_current_user)
):
    """Save Trello API credentials for the current user."""
    # Since we're not persisting in this version, just return success
    # In a real implementation, you would save these to a database
    return {
        "message": "Trello credentials saved successfully",
        "api_key": credentials.api_key,
        "token": "*****" # Don't return the actual token for security
    }

@router.get("/credentials")
async def get_trello_credentials(current_user: dict = Depends(get_current_user)):
    """Get Trello API credentials for the current user."""
    # In a real implementation, you would fetch this from the database
    # For now, just return no credentials
    return {
        "has_credentials": False,
        "api_key": None
    }

@router.post("/export", response_model=TrelloExportResponse)
async def export_to_trello(
    board_data: TrelloBoardCreate,
    current_user: dict = Depends(get_current_user)
):
    """Export a task and its subtasks to a Trello board."""
    # Get credentials from the request body
    api_key = board_data.api_key
    token = board_data.token

    # Credentials must be provided in the request
    if not api_key or not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trello credentials not found. Please add your Trello API key and token in settings."
        )
        
    print(f"Using Trello API key: {api_key[:5]}... for export")
    
    # Initialize task service
    task_service = TaskService()
    
    # Get the task tree
    task_tree = await task_service.get_task_tree(board_data.task_id)
    if not task_tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {board_data.task_id} not found"
        )
    
    # Create a new board in Trello
    async with httpx.AsyncClient() as client:
        # Create board
        board_response = await client.post(
            f"{TRELLO_API_BASE_URL}/boards",
            params={
                "name": board_data.name,
                "key": api_key,
                "token": token,
                "defaultLists": "false"  # Don't create default lists
            }
        )
        
        if board_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create Trello board: {board_response.text}"
            )
        
        board = board_response.json()
        board_id = board["id"]
        board_url = board["url"]
        
        # Create "Backlog" list
        list_response = await client.post(
            f"{TRELLO_API_BASE_URL}/lists",
            params={
                "name": "Backlog",
                "idBoard": board_id,
                "key": api_key,
                "token": token,
                "pos": "top"
            }
        )
        
        if list_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create Trello list: {list_response.text}"
            )
        
        list_id = list_response.json()["id"]
        
        # Create cards for tasks using BFS traversal
        await create_trello_cards_bfs(
            client, 
            task_tree, 
            list_id, 
            api_key, 
            token,
            parent_card_id=None
        )
    
    return {"board_url": board_url, "board_id": board_id}

async def create_trello_cards_bfs(client, task_tree, list_id, api_key, token, parent_card_id=None):
    """
    Perform BFS traversal of the task tree and create Trello cards for each task.
    Each card will have a link to its parent and the parent will have a checklist of child tasks.
    """
    # Create a queue for BFS traversal
    queue = [(task_tree, parent_card_id)]
    # Dictionary to store task_id -> card_id mapping
    card_mapping = {}
    
    while queue:
        current_task, parent_id = queue.pop(0)
        
        # Create card for current task
        card_data = {
            "name": current_task.description.split('\n')[0],  # First line as card title
            "desc": current_task.description,
            "idList": list_id,
            "key": api_key,
            "token": token,
        }
        
        # Add link to parent card if it exists
        if parent_id:
            card_data["desc"] += f"\n\nParent Task: https://trello.com/c/{parent_id}"
        
        card_response = await client.post(f"{TRELLO_API_BASE_URL}/cards", params=card_data)
        
        if card_response.status_code != 200:
            continue  # Skip this card if creation fails
        
        card = card_response.json()
        card_id = card["id"]
        card_mapping[current_task.task_id] = card_id
        
        # Add children to queue
        if hasattr(current_task, 'children') and current_task.children:
            # Create a checklist for child tasks
            checklist_response = await client.post(
                f"{TRELLO_API_BASE_URL}/cards/{card_id}/checklists",
                params={
                    "name": "Subtasks",
                    "key": api_key,
                    "token": token
                }
            )
            
            if checklist_response.status_code == 200:
                checklist_id = checklist_response.json()["id"]
                
                # Add children to queue and create checklist items
                for child in current_task.children:
                    queue.append((child, card_id))
                    
                    # Add checklist item
                    await client.post(
                        f"{TRELLO_API_BASE_URL}/checklists/{checklist_id}/checkItems",
                        params={
                            "name": child.description.split('\n')[0],
                            "key": api_key,
                            "token": token
                        }
                    )

@router.post("/start-export")
async def start_trello_export(
    request: TrelloStartExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start Trello export and return export ID for WebSocket connection"""
    # Generate export ID
    export_id = f"trello_export_{uuid.uuid4().hex[:8]}"
    
    # Start export in background
    asyncio.create_task(perform_trello_export(export_id, request, current_user))
    
    return {
        "export_id": export_id,
        "message": "Export started, connect to WebSocket for progress updates"
    }

async def perform_trello_export(export_id: str, request: TrelloStartExportRequest, current_user: dict):
    """Perform the actual Trello export with progress updates"""
    try:
        # Get credentials from request config
        api_key = request.config.trello_api_key
        token = request.config.trello_token
        board_name = request.config.board_name
        
        # Credentials must be provided in request (no persistence in this version)
        
        if not api_key or not token or not board_name:
            raise HTTPException(
                status_code=400, 
                detail="Trello credentials not found. Please configure Trello integration in Settings."
            )
        
        logger.info(f"Starting Trello export {export_id} for board: {board_name}")
        
        async def send_progress(step: str, progress: int, message: str):
            """Send progress update via WebSocket"""
            try:
                from app.websocket.manager import websocket_manager
                
                # Send to WebSocket clients connected to this export
                await websocket_manager.broadcast_to_task(
                    export_id,
                    {
                        "type": "trello.export.progress",
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

        # Step 1: Create board (0% to 20%)
        await send_progress("board_creation", 5, f"Creating Trello board '{board_name}'...")
        
        async with httpx.AsyncClient() as client:
            # Create board
            board_response = await client.post(
                f"{TRELLO_API_BASE_URL}/boards",
                params={
                    "name": board_name,
                    "key": api_key,
                    "token": token,
                    "defaultLists": "false"  # Don't create default lists, we'll create our own
                }
            )
            
            if board_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create Trello board: {board_response.text}"
                )
            
            board = board_response.json()
            board_id = board["id"]
            board_url = board["url"]
            
            await send_progress("board_creation", 20, f"Board '{board_name}' created successfully")

            # Step 2: Create lists (20% to 40%)
            await send_progress("list_creation", 25, "Creating board lists...")
            
            lists_to_create = ["Backlog", "To Do", "In Progress", "Done"]
            list_ids = {}
            
            for i, list_name in enumerate(lists_to_create):
                list_response = await client.post(
                    f"{TRELLO_API_BASE_URL}/lists",
                    params={
                        "name": list_name,
                        "idBoard": board_id,
                        "key": api_key,
                        "token": token,
                        "pos": "bottom"
                    }
                )
                
                if list_response.status_code == 200:
                    list_ids[list_name] = list_response.json()["id"]
                    progress = 25 + int((i + 1) / len(lists_to_create) * 15)
                    await send_progress("list_creation", progress, f"Created list: {list_name}")
            
            backlog_list_id = list_ids.get("Backlog", list(list_ids.values())[0])

            # Step 3: Create labels (40% to 50%)
            await send_progress("label_creation", 45, "Creating task labels...")
            
            labels_to_create = [
                {"name": "Story Points: 1", "color": "green"},
                {"name": "Story Points: 2", "color": "yellow"},
                {"name": "Story Points: 3", "color": "orange"},
                {"name": "Story Points: 5", "color": "red"},
                {"name": "Story Points: 8", "color": "purple"},
                {"name": "Story Points: 13", "color": "blue"},
                {"name": "Atomic Task", "color": "lime"},
                {"name": "Epic", "color": "pink"}
            ]
            
            for label in labels_to_create:
                await client.post(
                    f"{TRELLO_API_BASE_URL}/boards/{board_id}/labels",
                    params={
                        "name": label["name"],
                        "color": label["color"],
                        "key": api_key,
                        "token": token
                    }
                )
            
            await send_progress("label_creation", 50, "Labels created successfully")

            # Step 4: Create cards from task tree (50% to 90%)
            cards_created = 0
            
            def count_all_tasks(node: TaskNode) -> int:
                """Count all tasks in the tree"""
                count = 1
                if node.children:
                    for child in node.children:
                        count += count_all_tasks(child)
                return count

            total_tasks = count_all_tasks(request.task_tree)
            
            async def create_cards_from_tree(node: TaskNode, parent_card_id=None, depth=0):
                """Recursively create cards from task tree"""
                nonlocal cards_created
                
                # Create card for current task
                description = node.description
                if node.implementation_details:
                    description += f"\n\n**Implementation Details:**\n{node.implementation_details}"
                
                if parent_card_id:
                    description += f"\n\n**Parent Task:** [Link to parent card](https://trello.com/c/{parent_card_id})"
                
                card_data = {
                    "name": node.description.split('\n')[0][:255],  # First line as card title
                    "desc": description,
                    "idList": backlog_list_id,
                    "key": api_key,
                    "token": token,
                }
                
                progress = 50 + int((cards_created / total_tasks) * 40)
                await send_progress("card_creation", progress, 
                                  f"Creating card {cards_created + 1}/{total_tasks}: {node.description[:50]}...")
                
                card_response = await client.post(f"{TRELLO_API_BASE_URL}/cards", params=card_data)
                
                if card_response.status_code != 200:
                    logger.warning(f"Failed to create card for task {node.task_id}")
                    return None
                
                card = card_response.json()
                card_id = card["id"]
                cards_created += 1
                
                # Add labels based on task properties
                labels_to_add = []
                if node.story_points:
                    labels_to_add.append(f"Story Points: {node.story_points}")
                
                if node.is_atomic:
                    labels_to_add.append("Atomic Task")
                elif not node.children:
                    labels_to_add.append("Epic")
                
                # Add labels to card (simplified - just add to name for now)
                if labels_to_add:
                    label_text = " | ".join(labels_to_add)
                    await client.put(
                        f"{TRELLO_API_BASE_URL}/cards/{card_id}",
                        params={
                            "name": f"[{label_text}] {card_data['name']}"[:255],
                            "key": api_key,
                            "token": token
                        }
                    )
                
                # Create checklist for children if they exist
                if node.children:
                    checklist_response = await client.post(
                        f"{TRELLO_API_BASE_URL}/cards/{card_id}/checklists",
                        params={
                            "name": "Subtasks",
                            "key": api_key,
                            "token": token
                        }
                    )
                    
                    if checklist_response.status_code == 200:
                        checklist_id = checklist_response.json()["id"]
                        
                        # Add children to checklist and create their cards
                        for child in node.children:
                            # Add to checklist
                            await client.post(
                                f"{TRELLO_API_BASE_URL}/checklists/{checklist_id}/checkItems",
                                params={
                                    "name": child.description.split('\n')[0][:255],
                                    "key": api_key,
                                    "token": token
                                }
                            )
                            
                            # Recursively create child cards
                            await create_cards_from_tree(child, card_id, depth + 1)
                
                return card_id

            # Start creating cards from the root task
            if request.task_tree.children:
                for child in request.task_tree.children:
                    await create_cards_from_tree(child)
            else:
                await create_cards_from_tree(request.task_tree)

        await send_progress("completion", 100, f"Export completed! Created {cards_created} cards in Trello board")
        
        # Send success message
        try:
            from app.websocket.manager import websocket_manager
            result_data = {
                "success": True,
                "export_id": export_id,
                "board_name": board_name,
                "board_url": board_url,
                "board_id": board_id,
                "cards_created": cards_created
            }
            
            await websocket_manager.broadcast_to_task(
                export_id,
                {
                    "type": "trello.export.success",
                    "payload": result_data
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send success message: {e}")
        
        logger.info(f"Successfully created {cards_created} cards in Trello board {board_name}")

        return {
            "success": True,
            "export_id": export_id,
            "board_name": board_name,
            "board_url": board_url,
            "board_id": board_id,
            "cards_created": cards_created
        }

    except Exception as e:
        logger.error(f"Unexpected error during Trello export: {str(e)}")
        # Send error message via WebSocket
        try:
            from app.websocket.manager import websocket_manager
            await websocket_manager.broadcast_to_task(
                export_id,
                {
                    "type": "trello.export.error",
                    "payload": {
                        "message": str(e),
                        "export_id": export_id
                    }
                }
            )
        except Exception as ws_error:
            logger.error(f"Failed to send error via WebSocket: {ws_error}")
            
        raise
