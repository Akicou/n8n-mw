#!/usr/bin/env python3
"""
n8n MCP Server (HTTP Transport) - Control self-hosted n8n instances via MCP
Run this server and access it via HTTP transport
"""

import os
import json
from typing import Any, Optional
from datetime import datetime

import httpx
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent
import uvicorn

# Initialize MCP server
app = Server("n8n-server")

# Configuration
N8N_API_URL = os.getenv("N8N_API_URL", "http://localhost:5678/api/v1")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
SERVER_PORT = int(os.getenv("N8N_MCP_PORT", "8000"))
SERVER_HOST = os.getenv("N8N_MCP_HOST", "localhost")

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

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="list_workflows",
            description="List all workflows in the n8n instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "description": "Maximum number of workflows to return (default: 20)"},
                    "offset": {"type": "number", "description": "Number of workflows to skip (default: 0)"}
                }
            }
        ),
        Tool(
            name="get_workflow",
            description="Get a specific workflow by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The ID of the workflow to retrieve"}
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="get_workflow_by_name",
            description="Get a workflow by its name",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the workflow to retrieve"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="create_workflow",
            description="Create a new workflow in n8n",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the workflow"},
                    "nodes": {"type": "array", "description": "List of node objects"},
                    "connections": {"type": "object", "description": "Connection definitions between nodes"},
                    "settings": {"type": "object", "description": "Optional workflow settings"}
                },
                "required": ["name", "nodes", "connections"]
            }
        ),
        Tool(
            name="activate_workflow",
            description="Activate a workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID of the workflow to activate"}
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="deactivate_workflow",
            description="Deactivate a workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID of the workflow to deactivate"}
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="delete_workflow",
            description="Delete a workflow by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID of the workflow to delete"}
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="list_executions",
            description="List workflow executions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number"},
                    "offset": {"type": "number"},
                    "workflow_id": {"type": "string", "description": "Filter by workflow ID"},
                    "status": {"type": "string", "description": "Filter by status (error, success, waiting, running)"}
                }
            }
        ),
        Tool(
            name="get_execution",
            description="Get details of a specific execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string"}
                },
                "required": ["execution_id"]
            }
        ),
        Tool(
            name="execute_workflow",
            description="Manually execute a workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "data": {"type": "object", "description": "Input data for the workflow"}
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="execute_workflow_by_name",
            description="Execute a workflow by its name",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "data": {"type": "object", "description": "Input data for the workflow"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="list_webhooks",
            description="List all webhook paths in the n8n instance",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_webhook_url",
            description="Get the webhook URL for a specific workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"}
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="list_tags",
            description="List all tags in the n8n instance",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="create_tag",
            description="Create a new tag",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "color": {"type": "string", "description": "Optional color for the tag (hex format)"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="get_server_info",
            description="Get information about the n8n server instance",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    async def make_request(method: str, path: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=N8N_API_URL,
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            timeout=30.0
        ) as client:
            if method == "GET":
                return await client.get(path, **kwargs)
            elif method == "POST":
                return await client.post(path, **kwargs)
            elif method == "DELETE":
                return await client.delete(path, **kwargs)
            elif method == "PATCH":
                return await client.patch(path, **kwargs)

    result = ""

    try:
        if name == "list_workflows":
            response = await make_request("GET", "/workflows", params=arguments)
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "get_workflow":
            response = await make_request("GET", f"/workflows/{arguments['workflow_id']}")
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "get_workflow_by_name":
            response = await make_request("GET", "/workflows")
            handle_api_error(response)
            workflows = response.json().get("data", [])
            for workflow in workflows:
                if workflow.get("name") == arguments["name"]:
                    result = format_response(workflow)
                    break
            else:
                result = json.dumps({"error": f"Workflow '{arguments['name']}' not found"})

        elif name == "create_workflow":
            workflow_data = {
                "name": arguments["name"],
                "nodes": arguments.get("nodes", []),
                "connections": arguments.get("connections", {}),
                "settings": arguments.get("settings", {}),
                "active": False
            }
            response = await make_request("POST", "/workflows", json=workflow_data)
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "activate_workflow":
            response = await make_request("PATCH", f"/workflows/{arguments['workflow_id']}", json={"active": True})
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "deactivate_workflow":
            response = await make_request("PATCH", f"/workflows/{arguments['workflow_id']}", json={"active": False})
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "delete_workflow":
            response = await make_request("DELETE", f"/workflows/{arguments['workflow_id']}")
            handle_api_error(response)
            result = format_response({"success": True, "message": f"Workflow {arguments['workflow_id']} deleted"})

        elif name == "list_executions":
            params = {k: v for k, v in arguments.items() if v is not None}
            response = await make_request("GET", "/executions", params=params)
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "get_execution":
            response = await make_request("GET", f"/executions/{arguments['execution_id']}")
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "execute_workflow":
            execution_data = {}
            if "data" in arguments:
                execution_data["data"] = arguments["data"]
            response = await make_request("POST", f"/workflows/{arguments['workflow_id']}/execute", json=execution_data)
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "execute_workflow_by_name":
            list_response = await make_request("GET", "/workflows")
            handle_api_error(list_response)
            workflows = list_response.json().get("data", [])

            workflow_id = None
            for workflow in workflows:
                if workflow.get("name") == arguments["name"]:
                    workflow_id = workflow.get("id")
                    break

            if not workflow_id:
                result = json.dumps({"error": f"Workflow '{arguments['name']}' not found"})
            else:
                execution_data = {}
                if "data" in arguments:
                    execution_data["data"] = arguments["data"]
                response = await make_request("POST", f"/workflows/{workflow_id}/execute", json=execution_data)
                handle_api_error(response)
                result = format_response(response.json())

        elif name == "list_webhooks":
            response = await make_request("GET", "/webhooks")
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "get_webhook_url":
            response = await make_request("GET", f"/webhooks/workflow/{arguments['workflow_id']}")
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "list_tags":
            response = await make_request("GET", "/tags")
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "create_tag":
            tag_data = {"name": arguments["name"]}
            if "color" in arguments:
                tag_data["color"] = arguments["color"]
            response = await make_request("POST", "/tags", json=tag_data)
            handle_api_error(response)
            result = format_response(response.json())

        elif name == "get_server_info":
            base_url = N8N_API_URL.replace("/api/v1", "")
            response = await make_request("GET", "/active-workflows")
            handle_api_error(response)
            result = format_response({
                "api_url": N8N_API_URL,
                "base_url": base_url,
                "active_workflows": response.json()
            })

        else:
            result = json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        result = json.dumps({"error": str(e)})

    return [TextContent(type="text", text=result)]


# ==================== MAIN ====================

def main():
    """Start the HTTP MCP server and display connection info."""

    # Calculate the HTTP transport URL
    http_url = f"http://{SERVER_HOST}:{SERVER_PORT}/sse"

    print("=" * 70)
    print("n8n MCP Server (HTTP Transport)")
    print("=" * 70)
    print()
    print(f"HTTP Transport URL: {http_url}")
    print()
    print("To add this server to Claude Code, run:")
    print()
    print(f"   claude mcp add --transport http n8n {http_url}")
    print()
    print("Make sure to set these environment variables first:")
    print()
    print(f"   set N8N_API_URL={N8N_API_URL}")
    print("   set N8N_API_KEY=your-actual-api-key-here")
    print()
    print("=" * 70)
    print()
    print("Starting server on", f"{SERVER_HOST}:{SERVER_PORT}")
    print("Available tools:")
    tools = [
        "list_workflows", "get_workflow", "get_workflow_by_name", "create_workflow",
        "activate_workflow", "deactivate_workflow", "delete_workflow", "list_executions",
        "get_execution", "execute_workflow", "execute_workflow_by_name", "list_webhooks",
        "get_webhook_url", "list_tags", "create_tag", "get_server_info"
    ]
    for tool in tools:
        print(f"   - {tool}")
    print()
    print("Press Ctrl+C to stop the server")
    print()

    # Create SSE transport
    transport = SseServerTransport("/messages")

    # Run with uvicorn - use the SSE server properly
    from starlette.applications import Starlette
    from starlette.routing import Route

    # Create Starlette app with SSE endpoints
    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=app.create_sse_endpoint(transport)),
            Route("/messages", endpoint=app.create_post_endpoint(transport), methods=["POST"])
        ]
    )

    uvicorn.run(starlette_app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")


if __name__ == "__main__":
    main()
