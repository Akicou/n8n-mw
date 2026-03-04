#!/usr/bin/env python3
"""
n8n MCP Server - Control self-hosted n8n instances via MCP
"""

import os
import json
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("n8n-server")

# Configuration
N8N_API_URL = os.getenv("N8N_API_URL", "http://localhost:5678/api/v1")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

if not N8N_API_KEY:
    raise ValueError(
        "N8N_API_KEY environment variable is required. "
        "Set it with your n8n API key."
    )


def format_response(data: Any) -> str:
    """Format response data as JSON string."""
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


def handle_api_error(response: httpx.Response) -> None:
    """Handle API error responses."""
    if response.status_code >= 400:
        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise Exception(f"n8n API error ({response.status_code}): {error_data}")


# ==================== WORKFLOWS ====================

@mcp.tool()
async def list_workflows(limit: int = 20, offset: int = 0) -> str:
    """
    List all workflows in the n8n instance.

    Args:
        limit: Maximum number of workflows to return (default: 20)
        offset: Number of workflows to skip (default: 0)

    Returns:
        JSON string with workflow list
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(
            "/workflows",
            params={"limit": limit, "offset": offset}
        )
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def get_workflow(workflow_id: str) -> str:
    """
    Get a specific workflow by ID.

    Args:
        workflow_id: The ID of the workflow to retrieve

    Returns:
        JSON string with workflow details
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
async def get_workflow_by_name(name: str) -> str:
    """
    Get a workflow by its name.

    Args:
        name: The name of the workflow to retrieve

    Returns:
        JSON string with workflow details
    """
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


@mcp.tool()
async def create_workflow(
    name: str,
    nodes: list,
    connections: dict,
    settings: Optional[dict] = None,
    static_data: Optional[dict] = None
) -> str:
    """
    Create a new workflow in n8n.

    Args:
        name: Name of the workflow
        nodes: List of node objects
        connections: Connection definitions between nodes
        settings: Optional workflow settings
        static_data: Optional static data

    Returns:
        JSON string with created workflow details
    """
    workflow_data = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "settings": settings or {},
        "staticData": static_data or None,
        "active": False,
        "versionId": None
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
async def update_workflow(
    workflow_id: str,
    name: Optional[str] = None,
    nodes: Optional[list] = None,
    connections: Optional[dict] = None,
    settings: Optional[dict] = None,
    active: Optional[bool] = None
) -> str:
    """
    Update an existing workflow.

    Args:
        workflow_id: ID of the workflow to update
        name: New name for the workflow
        nodes: Updated node list
        connections: Updated connections
        settings: Updated settings
        active: Whether workflow should be active

    Returns:
        JSON string with updated workflow details
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        # First get current workflow
        get_response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(get_response)
        current = get_response.json()

        # Update fields
        update_data = {"id": workflow_id}
        if name is not None:
            update_data["name"] = name
        if nodes is not None:
            update_data["nodes"] = nodes
        if connections is not None:
            update_data["connections"] = connections
        if settings is not None:
            update_data["settings"] = settings
        if active is not None:
            update_data["active"] = active
        else:
            update_data["active"] = current.get("active", False)

        update_data["versionId"] = current.get("versionId")
        update_data["staticData"] = current.get("staticData")

        response = await client.patch(f"/workflows/{workflow_id}", json=update_data)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def delete_workflow(workflow_id: str) -> str:
    """
    Delete a workflow by ID.

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


@mcp.tool()
async def activate_workflow(workflow_id: str) -> str:
    """
    Activate a workflow.

    Args:
        workflow_id: ID of the workflow to activate

    Returns:
        JSON string with activation result
    """
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
    """
    Deactivate a workflow.

    Args:
        workflow_id: ID of the workflow to deactivate

    Returns:
        JSON string with deactivation result
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.patch(f"/workflows/{workflow_id}", json={"active": False})
        handle_api_error(response)
        return format_response(response.json())


# ==================== EXECUTIONS ====================

@mcp.tool()
async def list_executions(
    limit: int = 20,
    offset: int = 0,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    List workflow executions.

    Args:
        limit: Maximum number of executions to return
        offset: Number of executions to skip
        workflow_id: Filter by workflow ID
        status: Filter by status (error, success, waiting, running)

    Returns:
        JSON string with execution list
    """
    params = {"limit": limit, "offset": offset}
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
    """
    Get details of a specific execution.

    Args:
        execution_id: ID of the execution

    Returns:
        JSON string with execution details
    """
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
    """
    Delete an execution.

    Args:
        execution_id: ID of the execution to delete

    Returns:
        JSON string with deletion result
    """
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
    start_nodes: Optional[list] = None,
    destination_node: Optional[str] = None
) -> str:
    """
    Manually execute a workflow.

    Args:
        workflow_id: ID of the workflow to execute
        data: Input data for the workflow
        start_nodes: Specific nodes to start from
        destination_node: Run only until this node

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
    data: Optional[dict] = None,
    start_nodes: Optional[list] = None,
    destination_node: Optional[str] = None
) -> str:
    """
    Execute a workflow by its name.

    Args:
        name: Name of the workflow to execute
        data: Input data for the workflow
        start_nodes: Specific nodes to start from
        destination_node: Run only until this node

    Returns:
        JSON string with execution result
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        # First find the workflow by name
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

        # Execute the workflow
        execution_data = {}
        if data is not None:
            execution_data["data"] = data
        if start_nodes:
            execution_data["startNodes"] = start_nodes
        if destination_node:
            execution_data["destinationNode"] = destination_node

        response = await client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        handle_api_error(response)
        return format_response(response.json())


# ==================== WEBHOOKS ====================

@mcp.tool()
async def list_webhooks() -> str:
    """
    List all webhook paths in the n8n instance.

    Returns:
        JSON string with webhook list
    """
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
    """
    Get the webhook URL for a specific workflow.

    Args:
        workflow_id: ID of the workflow with a webhook node

    Returns:
        JSON string with webhook URL
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(f"/webhooks/workflow/{workflow_id}")
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def test_webhook(workflow_id: str, webhook_path: str) -> str:
    """
    Test a webhook endpoint.

    Args:
        workflow_id: ID of the workflow
        webhook_path: The webhook path to test

    Returns:
        JSON string with test result
    """
    # Construct full webhook URL
    base_url = N8N_API_URL.replace("/api/v1", "")
    webhook_url = f"{base_url}/webhook/{webhook_path}"

    async with httpx.AsyncClient(timeout=30.0) as test_client:
        response = await test_client.post(webhook_url, json={"test": True})

    return format_response({
        "status_code": response.status_code,
        "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
    })


# ==================== TAGS ====================

@mcp.tool()
async def list_tags() -> str:
    """
    List all tags in the n8n instance.

    Returns:
        JSON string with tag list
    """
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
    """
    Create a new tag.

    Args:
        name: Name of the tag
        color: Optional color for the tag (hex format)

    Returns:
        JSON string with created tag
    """
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
    """
    Delete a tag.

    Args:
        tag_id: ID of the tag to delete

    Returns:
        JSON string with deletion result
    """
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
    """
    List all credential types available in n8n.

    Returns:
        JSON string with credential types
    """
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
    """
    Get information about the n8n server instance.

    Returns:
        JSON string with server information
    """
    base_url = N8N_API_URL.replace("/api/v1", "")

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/active-workflows")
        handle_api_error(response)

        return format_response({
            "api_url": N8N_API_URL,
            "base_url": base_url,
            "active_workflows": response.json()
        })


# ==================== MAIN ====================

if __name__ == "__main__":
    mcp.run()
