#!/usr/bin/env python3
"""
n8n MCP Server - Control self-hosted n8n instances via MCP
Uses fastmcp for easy HTTP transport support
"""

import os
import json
import asyncio
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
    settings: Optional[dict] = None
) -> str:
    """
    Create a new workflow in n8n.

    Args:
        name: Name of the workflow
        nodes: List of node objects with id, name, type, position, parameters, etc.
        connections: Connection definitions between nodes
        settings: Optional workflow settings (executionOrder, saveManualExecutions, etc.)

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
    # Note: 'active' and 'tags' fields are read-only when creating workflows
    workflow_data = {
        "name": name,
        "nodes": nodes or [],
        "connections": connections or {},
        "settings": settings or {}
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
async def create_workflow_from_json(workflow_json: str | dict) -> str:
    """
    Create a workflow from a JSON string or dict (useful for importing/cloning).

    Args:
        workflow_json: Complete workflow definition as JSON string or dict

    Returns:
        JSON string with created workflow details
    """
    # Handle both string and dict input
    if isinstance(workflow_json, dict):
        workflow_data = workflow_json
    elif isinstance(workflow_json, str):
        try:
            workflow_data = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {e}"})
    else:
        return json.dumps({"error": "workflow_json must be a string or dict"})

    # Clean the workflow data - remove read-only fields
    workflow_data.pop("id", None)
    workflow_data.pop("active", None)
    workflow_data.pop("tags", None)
    workflow_data.pop("versionId", None)

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
    active: Optional[bool] = None
) -> str:
    """
    Update a workflow. Only provide the fields you want to change (partial update).

    Args:
        workflow_id: ID of the workflow to update
        name: New name for the workflow
        nodes: Updated node list (replaces all nodes)
        connections: Updated connections (replaces all connections)
        settings: Updated settings (merges with existing)
        active: Set active status (true/false)

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

        # Handle active parameter
        if active is not None:
            update_data["active"] = active
        else:
            update_data["active"] = current.get("active", False)

        update_data["tags"] = current.get("tags", [])
        update_data["versionId"] = current.get("versionId")
        update_data["staticData"] = current.get("staticData", None)

        # Use PUT instead of PATCH (PATCH not supported in this n8n version)
        response = await client.put(f"/workflows/{workflow_id}", json=update_data)
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


# ==================== NODE CREATION HELPERS ====================

@mcp.tool()
async def add_http_request_node(
    workflow_id: str,
    node_id: str,
    name: str,
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    body: Optional[dict] = None,
    position: Optional[list[int]] = None
) -> str:
    """
    Add an HTTP Request node to a workflow.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        url: The URL to send the request to
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        headers: Optional headers dictionary
        body: Optional JSON body for POST/PUT/PATCH
        position: Optional [x, y] position (default: [250, 300])

    Returns:
        JSON string with updated workflow
    """
    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "position": position or [250, 300],
        "parameters": {
            "method": method,
            "url": url
        }
    }

    if headers:
        node["parameters"]["headerParameters"] = {
            "parameters": [
                {"name": k, "value": v}
                for k, v in headers.items()
            ]
        }

    if body and method in ["POST", "PUT", "PATCH"]:
        node["parameters"]["bodyParameters"] = {
            "parameters": [
                {"name": k, "value": v}
                for k, v in body.items()
            ]
        }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_code_node(
    workflow_id: str,
    node_id: str,
    name: str,
    code: str,
    language: str = "javaScript",
    position: Optional[list[int]] = None
) -> str:
    """
    Add a Code node to execute JavaScript/Python code.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        code: The code to execute
        language: Programming language (javaScript or python)
        position: Optional [x, y] position

    Returns:
        JSON string with updated workflow
    """
    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.code",
        "position": position or [250, 300],
        "parameters": {
            "language": language,
            "code": code
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_webhook_node(
    workflow_id: str,
    node_id: str,
    name: str,
    path: str,
    http_method: str = "POST",
    response_mode: str = "responseNode",
    position: Optional[list[int]] = None
) -> str:
    """
    Add a Webhook node to trigger workflows via HTTP.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        path: The webhook path (e.g., "my-webhook")
        http_method: HTTP method (GET, POST, PUT, DELETE)
        response_mode: How to respond (onReceived, responseNode, lastNode)
        position: Optional [x, y] position

    Returns:
        JSON string with updated workflow
    """
    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.webhook",
        "position": position or [250, 300],
        "parameters": {
            "path": path,
            "httpMethod": http_method,
            "responseMode": response_mode
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_set_node(
    workflow_id: str,
    node_id: str,
    name: str,
    values: dict,
    position: Optional[list[int]] = None
) -> str:
    """
    Add a Set node to define/merge data values.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        values: Dictionary of key-value pairs to set
        position: Optional [x, y] position

    Returns:
        JSON string with updated workflow
    """
    parameters = []
    for i, (key, value) in enumerate(values.items()):
        parameters.append({
            "name": key,
            "value": value,
            "number": i
        })

    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.set",
        "position": position or [250, 300],
        "parameters": {
            "assignments": {
                "assignments": parameters
            }
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_if_node(
    workflow_id: str,
    node_id: str,
    name: str,
    condition: str,
    position: Optional[list[int]] = None
) -> str:
    """
    Add an IF node to split workflow based on conditions.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        condition: JavaScript expression (e.g., "{{ $json.status }} === 'success'")
        position: Optional [x, y] position

    Returns:
        JSON string with updated workflow
    """
    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.if",
        "position": position or [250, 300],
        "parameters": {
            "conditions": {
                "string": [
                    {
                        "number": 1,
                        "value": condition,
                        "output": 0
                    }
                ]
            }
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_merge_node(
    workflow_id: str,
    node_id: str,
    name: str,
    mode: str = "combine",
    position: Optional[list[int]] = None
) -> str:
    """
    Add a Merge node to combine/merge data from multiple inputs.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        mode: Merge mode (combine, append, merge, multiplex)
        position: Optional [x, y] position

    Returns:
        JSON string with updated workflow
    """
    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.merge",
        "position": position or [250, 300],
        "parameters": {
            "mode": mode
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_switch_node(
    workflow_id: str,
    node_id: str,
    name: str,
    rules: list[dict],
    position: Optional[list[int]] = None
) -> str:
    """
    Add a Switch node to route data based on multiple conditions.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        rules: List of rule dicts with 'name' and 'condition' keys
        position: Optional [x, y] position

    Example rules:
    [
        {"name": "High Priority", "condition": "{{ $json.priority }} > 5"},
        {"name": "Low Priority", "condition": "{{ $json.priority }} <= 5"}
    ]

    Returns:
        JSON string with updated workflow
    """
    rules_data = []
    for i, rule in enumerate(rules):
        rules_data.append({
            "name": rule.get("name", f"Rule {i+1}"),
            "conditions": {
                "string": [
                    {
                        "number": 1,
                        "value": rule.get("condition", ""),
                        "output": i
                    }
                ]
            }
        })

    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.switch",
        "position": position or [250, 300],
        "parameters": {
            "rules": {
                "values": rules_data
            }
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_loop_node(
    workflow_id: str,
    node_id: str,
    name: str,
    loop_over: str = "items",
    position: Optional[list[int]] = None
) -> str:
    """
    Add a Loop Over Items node to iterate over arrays.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        loop_over: Field to loop over (default: "items")
        position: Optional [x, y] position

    Returns:
        JSON string with updated workflow
    """
    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.splitInBatches",
        "position": position or [250, 300],
        "parameters": {
            "fieldToLoopOver": loop_over,
            "options": {}
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_wait_node(
    workflow_id: str,
    node_id: str,
    name: str,
    wait_time: int = 1,
    unit: str = "seconds",
    position: Optional[list[int]] = None
) -> str:
    """
    Add a Wait node to pause execution.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the node
        wait_time: Amount of time to wait
        unit: Time unit (seconds, minutes, hours)
        position: Optional [x, y] position

    Returns:
        JSON string with updated workflow
    """
    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.wait",
        "position": position or [250, 300],
        "parameters": {
            "amount": wait_time,
            "unit": unit
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def add_note_node(
    workflow_id: str,
    node_id: str,
    name: str,
    content: str,
    position: Optional[list[int]] = None
) -> str:
    """
    Add a sticky note to document the workflow.

    Args:
        workflow_id: ID of the workflow
        node_id: Unique ID for the node
        name: Display name for the note
        content: The note content/text
        position: Optional [x, y] position

    Returns:
        JSON string with updated workflow
    """
    node = {
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.stickyNote",
        "position": position or [250, 300],
        "parameters": {
            "content": content,
            "height": 200,
            "width": 200
        }
    }

    return await add_node_to_workflow(workflow_id, node)


@mcp.tool()
async def connect_nodes(
    workflow_id: str,
    source_node_id: str,
    target_node_id: str,
    source_output_index: int = 0,
    target_input_index: int = 0
) -> str:
    """
    Connect two nodes in a workflow.

    Args:
        workflow_id: ID of the workflow
        source_node_id: ID of the source node
        target_node_id: ID of the target node
        source_output_index: Output index on source (default: 0)
        target_input_index: Input index on target (default: 0)

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

        connections = current.get("connections", {})

        # Initialize connections structure for source node if not exists
        if source_node_id not in connections:
            connections[source_node_id] = {"main": [[], []]}

        # Add the connection
        connections[source_node_id]["main"][source_output_index].append({
            "node": target_node_id,
            "type": "main",
            "index": target_input_index
        })

        return await update_workflow(workflow_id, connections=connections)


@mcp.tool()
async def disconnect_nodes(
    workflow_id: str,
    source_node_id: str,
    target_node_id: str
) -> str:
    """
    Disconnect two nodes in a workflow.

    Args:
        workflow_id: ID of the workflow
        source_node_id: ID of the source node
        target_node_id: ID of the target node to disconnect

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

        connections = current.get("connections", {})

        # Remove the connection
        if source_node_id in connections:
            main_outputs = connections[source_node_id].get("main", [])
            for output_idx, connections_list in enumerate(main_outputs):
                # Filter out the target connection
                main_outputs[output_idx] = [
                    conn for conn in connections_list
                    if conn.get("node") != target_node_id
                ]

        return await update_workflow(workflow_id, connections=connections)


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

        # Create a copy with new name (remove id, active, and tags as they're read-only)
        workflow_data = {
            "name": new_name,
            "nodes": source.get("nodes", []),
            "connections": source.get("connections", {}),
            "settings": source.get("settings", {}),
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
        # First get the workflow to get its current state
        get_response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(get_response)
        workflow = get_response.json()

        # Update with active=True using PUT
        workflow["active"] = True
        response = await client.put(f"/workflows/{workflow_id}", json=workflow)
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
        # First get the workflow to get its current state
        get_response = await client.get(f"/workflows/{workflow_id}")
        handle_api_error(get_response)
        workflow = get_response.json()

        # Update with active=False using PUT
        workflow["active"] = False
        response = await client.put(f"/workflows/{workflow_id}", json=workflow)
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


# ==================== DEBUGGING TOOLS ====================

@mcp.tool()
async def test_workflow(
    workflow_id: str,
    data: Optional[dict] = None,
    start_nodes: Optional[list[str]] = None
) -> str:
    """
    Test/execute a workflow in "manual execution" mode for debugging.
    This executes the workflow and returns detailed execution data.

    Args:
        workflow_id: ID of the workflow to test
        data: Test data to send to the workflow
        start_nodes: Optional nodes to start from (for partial testing)

    Returns:
        JSON string with execution details including status, runtime, and results
    """
    execution_data = {}
    if data is not None:
        execution_data["data"] = data
    if start_nodes:
        execution_data["startNodes"] = start_nodes

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=60.0  # Longer timeout for testing
    ) as client:
        response = await client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        handle_api_error(response)
        return format_response(response.json())


@mcp.tool()
async def debug_execution(execution_id: str) -> str:
    """
    Get detailed debugging information about an execution.
    Includes node-by-node execution data, errors, and output.

    Args:
        execution_id: ID of the execution to debug

    Returns:
        JSON string with detailed execution debug info
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(f"/executions/{execution_id}")
        handle_api_error(response)
        execution = response.json()

        # Format debug information
        debug_info = {
            "execution_id": execution.get("id"),
            "workflow_id": execution.get("workflowId"),
            "status": execution.get("status"),
            "mode": execution.get("mode"),
            "started_at": execution.get("startedAt"),
            "stopped_at": execution.get("stoppedAt"),
            "runtime_ms": execution.get("finishedAt") and execution.get("waitTill"),
            "data": execution.get("data"),
            "result_data": execution.get("resultData"),
            "error": execution.get("error"),
            "execution_data": execution.get("executionData")
        }

        return format_response(debug_info)


@mcp.tool()
async def get_execution_logs(execution_id: str) -> str:
    """
    Get detailed logs for a specific execution including node execution order.

    Args:
        execution_id: ID of the execution

    Returns:
        JSON string with execution logs and timeline
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(f"/executions/{execution_id}")
        handle_api_error(response)
        execution = response.json()

        logs = {
            "execution_id": execution.get("id"),
            "workflow_id": execution.get("workflowId"),
            "status": execution.get("status"),
            "started_at": execution.get("startedAt"),
            "stopped_at": execution.get("stoppedAt"),
            "nodes_execution": execution.get("executionData", {}).get("contextData", {}).get("nodeExecutionStack", []),
            "result_data": execution.get("resultData", {}),
            "workflow_data": execution.get("data", {})
        }

        return format_response(logs)


@mcp.tool()
async def get_workflow_executions(
    workflow_id: str,
    limit: int = 10,
    status: Optional[str] = None
) -> str:
    """
    Get all executions for a specific workflow, ordered by most recent.

    Args:
        workflow_id: ID of the workflow
        limit: Maximum number of executions to return
        status: Optional filter by status (error, success, waiting, running)

    Returns:
        JSON string with workflow execution history
    """
    params = {"workflowId": workflow_id, "limit": limit}
    if status:
        params["status"] = status

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/executions", params=params)
        handle_api_error(response)

        executions = response.json().get("data", [])

        # Format execution summary
        summary = {
            "workflow_id": workflow_id,
            "total_executions": len(executions),
            "executions": [
                {
                    "id": ex.get("id"),
                    "status": ex.get("status"),
                    "started_at": ex.get("startedAt"),
                    "finished_at": ex.get("finishedAt"),
                    "mode": ex.get("mode"),
                    "retry_of": ex.get("retryOf"),
                    "retry_success_id": ex.get("retrySuccessId")
                }
                for ex in executions
            ]
        }

        return format_response(summary)


@mcp.tool()
async def get_failed_executions(workflow_id: Optional[str] = None, limit: int = 20) -> str:
    """
    Get only failed executions for debugging.

    Args:
        workflow_id: Optional workflow ID to filter by
        limit: Maximum number of failed executions to return

    Returns:
        JSON string with failed executions and error details
    """
    params = {"status": "error", "limit": limit}
    if workflow_id:
        params["workflowId"] = workflow_id

    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get("/executions", params=params)
        handle_api_error(response)

        executions = response.json().get("data", [])

        # Format error summary
        errors = []
        for ex in executions:
            error_info = {
                "execution_id": ex.get("id"),
                "workflow_id": ex.get("workflowId"),
                "started_at": ex.get("startedAt"),
                "error": ex.get("error"),
                "last_node_executed": ex.get("executionData", {}).get("lastNodeExecuted")
            }
            errors.append(error_info)

        return format_response({
            "total_failed": len(errors),
            "errors": errors
        })


@mcp.tool()
async def get_execution_result(execution_id: str) -> str:
    """
    Get the final result/output data from an execution.

    Args:
        execution_id: ID of the execution

    Returns:
        JSON string with execution result data
    """
    async with httpx.AsyncClient(
        base_url=N8N_API_URL,
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=30.0
    ) as client:
        response = await client.get(f"/executions/{execution_id}")
        handle_api_error(response)
        execution = response.json()

        return format_response({
            "execution_id": execution.get("id"),
            "status": execution.get("status"),
            "result_data": execution.get("resultData", {}),
            "workflow_output": execution.get("data"),
            "error": execution.get("error")
        })


@mcp.tool()
async def wait_for_execution(
    execution_id: str,
    timeout: int = 60
) -> str:
    """
    Wait for an execution to complete and return the final result.
    Useful for testing synchronous workflows.

    Args:
        execution_id: ID of the execution to wait for
        timeout: Maximum seconds to wait (default: 60)

    Returns:
        JSON string with final execution status and results
    """
    import asyncio

    start_time = asyncio.get_event_loop().time()
    poll_interval = 1  # Check every second

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        async with httpx.AsyncClient(
            base_url=N8N_API_URL,
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            timeout=30.0
        ) as client:
            response = await client.get(f"/executions/{execution_id}")
            handle_api_error(response)
            execution = response.json()

            status = execution.get("status")
            if status in ["success", "error", "crashed"]:
                return format_response({
                    "execution_id": execution.get("id"),
                    "status": status,
                    "result_data": execution.get("resultData", {}),
                    "error": execution.get("error"),
                    "waited_seconds": round(asyncio.get_event_loop().time() - start_time)
                })

        await asyncio.sleep(poll_interval)

    return format_response({
        "error": "Timeout waiting for execution to complete",
        "execution_id": execution_id,
        "last_status": execution.get("status")
    })


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
