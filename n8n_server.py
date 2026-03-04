#!/usr/bin/env python3
"""
n8n MCP Server - Control self-hosted n8n instances via MCP
Uses fastmcp for easy HTTP transport support
"""

import os
import json
from typing import Any, Optional
from dotenv import load_dotenv

import httpx
from fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("n8n-server")

# Configuration
N8N_API_URL = os.getenv("N8N_API_URL", "http://localhost:5678/api/v1")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


def format_response(data: Any) -> str:
    """Format response data as JSON string."""
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


def handle_api_error(response: httpx.Response) -> None:
    """Handle API error responses."""
    if response.status_code >= 400:
        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise Exception(f"n8n API error ({response.status_code}): {error_data}")


# ==================== WORKFLOWS - LIST & GET ====================

@mcp.tool()
async def list_workflows(
    limit: int = 20,
    active: Optional[bool] = None
) -> str:
    """
    List all workflows in the n8n instance with optional filtering.

    Args:
        limit: Maximum number of workflows to return (default: 20)
        active: Filter by active status (true/false, or null for all)

    Returns:
        JSON string with workflow list
    """
    params = {}
    if limit:
        params["limit"] = limit
    if active is not None:
        params["active"] = "true" if active else "false"

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/workflows", params=params)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def get_workflow(workflow_id: str) -> str:
    """Get a specific workflow by ID with full details including nodes and connections."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def get_workflow_by_name(name: str) -> str:
    """Get a workflow by its name (searches all workflows)."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/workflows")
        handle_api_error(response)
        workflows = response.json().get("data", [])

        for workflow in workflows:
            if workflow.get("name") == name:
                return format_response(workflow)

        return json.dumps({"error": f"Workflow '{name}' not found"})


# ==================== WORKFLOWS - CREATE ====================

@mcp.tool()
async def create_workflow(
    name: str,
    nodes: Optional[list] = None,
    connections: Optional[dict] = None,
    settings: Optional[dict] = None,
    tags: Optional[list[str]] = None
) -> str:
    """
    Create a new workflow in n8n.

    Args:
        name: Name of the workflow
        nodes: List of node objects with id, name, type, position, parameters, etc.
        connections: Connection definitions between nodes
        settings: Optional workflow settings (executionOrder, saveManualExecutions, etc.)
        tags: Optional list of tag IDs to associate with the workflow

    Returns:
        JSON string with created workflow details

    Example nodes format:
    [
        {
            "id": "unique-id",
            "name": "My Node",
            "type": "n8n-nodes-base.httpRequest",
            "position": [250, 300],
            "parameters": {"url": "https://example.com"}
        }
    ]
    """
    # Note: 'active' field is read-only when creating workflows
    workflow_data = {
        "name": name,
        "nodes": nodes or [],
        "connections": connections or {},
        "settings": settings or {},
        "tags": tags or []
    }

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.post("/workflows", json=workflow_data)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def create_workflow_from_json(workflow_json: str) -> str:
    """
    Create a workflow from a JSON string (useful for importing/cloning).

    Args:
        workflow_json: Complete workflow definition as JSON string

    Returns:
        JSON string with created workflow details
    """
    try:
        workflow_data = json.loads(workflow_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.post("/workflows", json=workflow_data)
        handle_api_error(response)
        return format_response(response.json())


# ==================== WORKFLOWS - UPDATE/EDIT ====================

@mcp.tool()
async def update_workflow(
    workflow_id: str,
    name: Optional[str] = None,
    nodes: Optional[list] = None,
    connections: Optional[dict] = None,
    settings: Optional[dict] = None,
    tags: Optional[list[str]] = None
) -> str:
    """
    Update a workflow. Only provide the fields you want to change (partial update).

    Args:
        workflow_id: ID of the workflow to update
        name: New name for the workflow
        nodes: Updated node list (replaces all nodes)
        connections: Updated connections (replaces all connections)
        settings: Updated settings (merges with existing)
        tags: Updated tag list

    Returns:
        JSON string with updated workflow details
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        # Get current workflow first
        get_response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(get_response)
        current = get_response.json()

        # Build update data with only provided fields
        update_data = {"id": workflow_id}

        if name is not None:
            update_data["name"] = name
        else:
            update_data["name"] = current.get("name", "")

        if nodes is not None:
            update_data["nodes"] = nodes
        else:
            update_data["nodes"] = current.get("nodes", [])

        if connections is not None:
            update_data["connections"] = connections
        else:
            update_data["connections"] = current.get("connections", {})

        if settings is not None:
            # Merge settings
            existing_settings = current.get("settings", {})
            update_data["settings"] = {**existing_settings, **settings}
        else:
            update_data["settings"] = current.get("settings", {})

        if tags is not None:
            update_data["tags"] = tags
        else:
            update_data["tags"] = current.get("tags", [])

        update_data["active"] = current.get("active", False)
        update_data["versionId"] = current.get("versionId")
        update_data["staticData"] = current.get("staticData", None)

        response = await client.patch(f"/workflows/{workflow_id}", json=update_data)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def rename_workflow(workflow_id: str, new_name: str) -> str:
    """
    Quick helper to rename a workflow.

    Args:
        workflow_id: ID of the workflow to rename
        new_name: New name for the workflow

    Returns:
        JSON string with updated workflow
    """
    return await update_workflow(workflow_id, name=new_name)


@mcp.tool()
async def update_workflow_settings(
    workflow_id: str,
    settings: dict
) -> str:
    """
    Update only the settings of a workflow (preserves nodes and connections).

    Args:
        workflow_id: ID of the workflow
        settings: Settings object (e.g., {"executionOrder": "v1"})

    Returns:
        JSON string with updated workflow
    """
    return await update_workflow(workflow_id, settings=settings)


@mcp.tool()
async def add_node_to_workflow(
    workflow_id: str,
    node: dict
) -> str:
    """
    Add a single node to an existing workflow.

    Args:
        workflow_id: ID of the workflow
        node: Node object to add (must include id, name, type, position)

    Returns:
        JSON string with updated workflow

    Example node:
    {
        "id": "new-node-id",
        "name": "HTTP Request",
        "type": "n8n-nodes-base.httpRequest",
        "position": [500, 300],
        "parameters": {"method": "GET", "url": "https://api.example.com"}
    }
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        get_response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(get_response)
        current = get_response.json()

        nodes = current.get("nodes", [])
        nodes.append(node)

        return await update_workflow(workflow_id, nodes=nodes)


@mcp.tool()
async def remove_node_from_workflow(
    workflow_id: str,
    node_id: str
) -> str:
    """
    Remove a node from a workflow by its ID.

    Args:
        workflow_id: ID of the workflow
        node_id: ID of the node to remove

    Returns:
        JSON string with updated workflow
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        get_response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(get_response)
        current = get_response.json()

        nodes = [n for n in current.get("nodes", []) if n.get("id") != node_id]

        return await update_workflow(workflow_id, nodes=nodes)


# ==================== WORKFLOWS - CLONE/IMPORT/EXPORT ====================

@mcp.tool()
async def clone_workflow(
    workflow_id: str,
    new_name: str
) -> str:
    """
    Clone/copy a workflow with a new name.

    Args:
        workflow_id: ID of the workflow to clone
        new_name: Name for the cloned workflow

    Returns:
        JSON string with the new workflow details
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        # Get the source workflow
        get_response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(get_response)
        source = get_response.json()

        # Create a copy with new name (remove id to create new)
        # Note: 'active' field is read-only when creating, so we don't include it
        workflow_data = {
            "name": new_name,
            "nodes": source.get("nodes", []),
            "connections": source.get("connections", {}),
            "settings": source.get("settings", {}),
            "tags": source.get("tags", []),
            "staticData": source.get("staticData", None)
        }

        response = await client.post("/workflows", json=workflow_data)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def export_workflow(workflow_id: str) -> str:
    """
    Export a workflow as JSON (for backup or import).

    Args:
        workflow_id: ID of the workflow to export

    Returns:
        JSON string of the complete workflow definition
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def import_workflow(workflow_json: str) -> str:
    """
    Import a workflow from JSON (same as create_workflow_from_json).

    Args:
        workflow_json: Workflow definition as JSON string

    Returns:
        JSON string with imported workflow details
    """
    return await create_workflow_from_json(workflow_json)


# ==================== WORKFLOWS - ACTIVATE/DELETE ====================

@mcp.tool()
async def activate_workflow(workflow_id: str) -> str:
    """Activate a workflow."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.patch(f"/workflows/{workflow_id}", json={"active": True})
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def deactivate_workflow(workflow_id: str) -> str:
    """Deactivate a workflow."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.patch(f"/workflows/{workflow_id}", json={"active": False})
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def delete_workflow(workflow_id: str) -> str:
    """
    Delete a workflow by ID. WARNING: This cannot be undone!

    Args:
        workflow_id: ID of the workflow to delete

    Returns:
        JSON string with deletion result
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.delete(f"/workflows/{workflow_id}")
        handle_api_error(response)
        return format_response({"success": True, "message": f"Workflow {workflow_id} deleted"})


# ==================== EXECUTIONS ====================

@mcp.tool()
async def list_executions(
    limit: int = 20,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    List workflow executions with filtering.

    Args:
        limit: Maximum number of executions to return
        workflow_id: Filter by workflow ID
        status: Filter by status (error, success, waiting, running)

    Returns:
        JSON string with execution list
    """
    params = {}
    if limit:
        params["limit"] = limit
    if workflow_id:
        params["workflowId"] = workflow_id
    if status:
        params["status"] = status

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/executions", params=params)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def get_execution(execution_id: str) -> str:
    """Get details of a specific execution including input/output data."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(f"/executions/{execution_id}")
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def delete_execution(execution_id: str) -> str:
    """Delete an execution."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.delete(f"/executions/{execution_id}")
        handle_api_error(response)
        return format_response({"success": True, "message": f"Execution {execution_id} deleted"})


@mcp.tool()
async def retry_execution(execution_id: str) -> str:
    """
    Retry a failed execution.

    Args:
        execution_id: ID of the execution to retry

    Returns:
        JSON string with retry result
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.post(f"/executions/{execution_id}/retry")
        handle_api_error(response)
        return format_response(response.json())


# ==================== MANUAL EXECUTION ====================

@mcp.tool()
async def execute_workflow(
    workflow_id: str,
    data: Optional[dict] = None,
    start_nodes: Optional[list[str]] = None,
    destination_node: Optional[str] = None
) -> str:
    """
    Manually execute a workflow with custom options.

    Args:
        workflow_id: ID of the workflow to execute
        data: Input data for the workflow
        start_nodes: Specific nodes to start from (partial execution)
        destination_node: Run only until this node (partial execution)

    Returns:
        JSON string with execution result
    """
    execution_data = {}
    if data is not None:
        execution_data["data"] = data
    if start_nodes:
        execution_data["startNodes"] = start_nodes
    if destination_node:
        execution_data["destinationNode"] = destination_node

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def execute_workflow_by_name(
    name: str,
    data: Optional[dict] = None
) -> str:
    """Execute a workflow by its name."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        list_response = await client.get("/workflows")
        handle_api_error(list_response)
        workflows = list_response.json().get("data", [])

        workflow_id = None
        for workflow in workflows:
            if workflow.get("name") == name:
                workflow_id = workflow.get("id")
                break

        if not workflow_id:
            return json.dumps({"error": f"Workflow '{name}' not found"})

        execution_data = {}
        if data is not None:
            execution_data["data"] = data

        response = await client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        handle_api_error(response)
        return format_response(response.json())


# ==================== WEBHOOKS ====================

@mcp.tool()
async def list_webhooks() -> str:
    """List all webhook paths in the n8n instance."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/webhooks")
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def get_webhook_url(workflow_id: str) -> str:
    """Get the webhook URL for a specific workflow."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(f"/webhooks/workflow/{workflow_id}")
        handle_api_error(response)
        return format_response(response.json())


# ==================== TAGS ====================

@mcp.tool()
async def list_tags() -> str:
    """List all tags in the n8n instance."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/tags")
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def create_tag(name: str, color: Optional[str] = None) -> str:
    """Create a new tag."""
    tag_data = {"name": name}
    if color:
        tag_data["color"] = color

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.post("/tags", json=tag_data)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def delete_tag(tag_id: str) -> str:
    """Delete a tag."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.delete(f"/tags/{tag_id}")
        handle_api_error(response)
        return format_response({"success": True, "message": f"Tag {tag_id} deleted"})


# ==================== CREDENTIALS ====================

@mcp.tool()
async def list_credentials() -> str:
    """List all credential types available in n8n."""
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/credentials")
        handle_api_error(response)
        return format_response(response.json())


# ==================== SYSTEM INFO ====================

@mcp.tool()
async def get_server_info() -> str:
    """Get information about the n8n server instance."""
    base_url = N8N_API_URL.replace("/api/v1", "")

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        # Get active workflows
        response = await client.get("/workflows", params={"active": "true"})
        handle_api_error(response)
        active = response.json().get("data", [])

        # Get total workflow count
        all_response = await client.get("/workflows")
        handle_api_error(all_response)
        all_workflows = all_response.json().get("data", [])

        return format_response({
            "api_url": N8N_API_URL,
            "base_url": base_url,
            "active_workflow_count": len(active),
            "total_workflow_count": len(all_workflows),
            "active_workflows": [{"id": w.get("id"), "name": w.get("name")} for w in active]
        })


if __name__ == "__main__":
    # This will be run by fastmcp CLI
    mcp.run()
