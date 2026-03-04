# n8n MCP Server

A comprehensive [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that allows AI assistants to control self-hosted [n8n](https://n8n.io/) workflow automation instances.

## Features

- **Full workflow management**: Create, read, update, clone, delete, activate/deactivate workflows
- **Node-specific tools**: Add HTTP requests, webhooks, code nodes, conditions, loops, and more
- **Execution control**: Manually execute workflows, retry failed executions, view execution history
- **Workflow connections**: Connect and disconnect nodes programmatically
- **Webhook management**: List webhooks and get webhook URLs
- **Tag management**: Create, list, and delete organizational tags
- **Import/Export**: Backup and restore workflows as JSON

## Installation

### Prerequisites

- Python 3.10 or higher
- A running n8n instance with API access enabled
- n8n API key (get it from n8n Settings > API > Create API Key)

### Setup

1. **Clone or navigate to the project:**
   ```bash
   cd n8n-mw
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   Create a `.env` file in the project directory:
   ```env
   N8N_API_URL=https://your-n8n-instance.com/api/v1
   N8N_API_KEY=your-n8n-api-key-here
   ```

   Or set them as system environment variables.

## Running the Server

### Start the HTTP Server

```bash
fastmcp run n8n_server.py --transport http
```

The server will start on `http://127.0.0.1:8000/mcp` by default.

## Connecting to Claude Code

### Add the MCP Server

```bash
claude mcp add --transport http n8n http://127.0.0.1:8000/mcp
```

### Verify Connection

In Claude Code, run `/mcp` to see the connected servers. You should see `n8n` listed.

## Available Tools (54 Total)

### Workflow Basics

| Tool | Description |
|------|-------------|
| `list_workflows` | List all workflows with optional filtering |
| `get_workflow` | Get a workflow by ID |
| `get_workflow_by_name` | Get a workflow by name |
| `create_workflow` | Create a new workflow |
| `create_workflow_from_json` | Create from JSON string |
| `update_workflow` | Update workflow (partial updates supported) |
| `rename_workflow` | Quick rename helper |
| `delete_workflow` | Delete a workflow |
| `activate_workflow` | Activate a workflow |
| `deactivate_workflow` | Deactivate a workflow |

### Workflow Advanced

| Tool | Description |
|------|-------------|
| `clone_workflow` | Clone/copy a workflow |
| `export_workflow` | Export workflow as JSON |
| `import_workflow` | Import workflow from JSON |
| `update_workflow_settings` | Update only settings |
| `get_server_info` | Get server information and stats |

### Node Management

| Tool | Description |
|------|-------------|
| `add_node_to_workflow` | Add a custom node |
| `remove_node_from_workflow` | Remove a node by ID |
| `connect_nodes` | Connect two nodes |
| `disconnect_nodes` | Disconnect two nodes |

### Node Creation Helpers

| Tool | Description |
|------|-------------|
| `add_http_request_node` | Add HTTP Request node |
| `add_code_node` | Add JavaScript/Python code node |
| `add_webhook_node` | Add webhook trigger |
| `add_set_node` | Add data transformation node |
| `add_if_node` | Add conditional logic |
| `add_switch_node` | Add multi-way routing |
| `add_merge_node` | Add data merging |
| `add_loop_node` | Add loop over items |
| `add_wait_node` | Add delay/wait |
| `add_note_node` | Add documentation note |

### Executions

| Tool | Description |
|------|-------------|
| `list_executions` | List execution history |
| `get_execution` | Get execution details |
| `execute_workflow` | Manually execute workflow |
| `execute_workflow_by_name` | Execute by name |
| `retry_execution` | Retry failed execution |
| `delete_execution` | Delete execution record |

### Debugging & Testing

| Tool | Description |
|------|-------------|
| `test_workflow` | Test/execute workflow for debugging |
| `debug_execution` | Get detailed node-by-node execution data |
| `get_execution_logs` | Get execution logs and timeline |
| `get_workflow_executions` | Get all executions for a workflow |
| `get_failed_executions` | Get only failed executions with errors |
| `get_execution_result` | Get final output data from execution |
| `wait_for_execution` | Wait for execution to complete (sync) |

### Webhooks

| Tool | Description |
|------|-------------|
| `list_webhooks` | List all webhooks |
| `get_webhook_url` | Get webhook URL for workflow |

### Tags & Credentials

| Tool | Description |
|------|-------------|
| `list_tags` | List all tags |
| `create_tag` | Create a new tag |
| `delete_tag` | Delete a tag |
| `list_credentials` | List credential types |

## Usage Examples

### Example 1: List All Workflows

```python
# List all active workflows
list_workflows(active=True)
```

### Example 2: Create a Simple Webhook Workflow

```python
# Create a new workflow
workflow = create_workflow(name="My Webhook Workflow")

# Add a webhook trigger
add_webhook_node(
    workflow_id=workflow["id"],
    node_id="webhook-1",
    name="Webhook",
    path="my-webhook",
    http_method="POST"
)

# Add an HTTP request node
add_http_request_node(
    workflow_id=workflow["id"],
    node_id="http-1",
    name="Call API",
    url="https://api.example.com/endpoint",
    method="POST",
    position=[500, 300]
)

# Connect the nodes
connect_nodes(
    workflow_id=workflow["id"],
    source_node_id="webhook-1",
    target_node_id="http-1"
)

# Activate the workflow
activate_workflow(workflow_id=workflow["id"])
```

### Example 3: Clone and Modify Workflow

```python
# Clone existing workflow
cloned = clone_workflow(
    workflow_id="original-workflow-id",
    new_name="My Cloned Workflow"
)

# Add a code node to transform data
add_code_node(
    workflow_id=cloned["id"],
    node_id="code-1",
    name="Transform Data",
    code="return { transformed: $json.data.toUpperCase() };",
    position=[750, 300]
)

# Connect it to the workflow
connect_nodes(
    workflow_id=cloned["id"],
    source_node_id="existing-node-id",
    target_node_id="code-1"
)
```

### Example 4: Execute Workflow with Data

```python
# Execute a workflow with custom data
result = execute_workflow(
    workflow_id="my-workflow-id",
    data={
        "user": "john_doe",
        "action": "sync"
    }
)
```

### Example 5: Create Conditional Routing

```python
# Add a switch node for multi-way routing
add_switch_node(
    workflow_id=workflow_id,
    node_id="switch-1",
    name="Route by Priority",
    rules=[
        {"name": "High", "condition": "{{ $json.priority }} > 5"},
        {"name": "Medium", "condition": "{{ $json.priority }} > 2"},
        {"name": "Low", "condition": "{{ $json.priority }} <= 2"}
    ]
)
```

### Example 6: Test and Debug a Workflow

```python
# Test a workflow with sample data
test_result = test_workflow(
    workflow_id="my-workflow-id",
    data={"test": "data", "user_id": "12345"}
)

# Get detailed execution debug info
debug_info = debug_execution(execution_id=test_result["execution_id"])

# View execution logs
logs = get_execution_logs(execution_id=test_result["execution_id"])

# Get only failed executions for analysis
failed = get_failed_executions(workflow_id="my-workflow-id")

# Wait for a long-running execution to complete
final_result = wait_for_execution(
    execution_id="running-execution-id",
    timeout=120  # Wait up to 2 minutes
)
```

### Example 7: Analyze Workflow Executions

```python
# Get recent executions for a workflow
history = get_workflow_executions(
    workflow_id="my-workflow-id",
    limit=20
)

# Check for failures
errors = get_failed_executions(workflow_id="my-workflow-id")

# Get the result output from an execution
output = get_execution_result(execution_id="execution-id")
```

## Node Positioning

When adding nodes, use `position` parameter to place them visually:

```python
# Format: [x, y] in pixels
position=[250, 300]   # Default position
position=[500, 300]   # To the right
position=[250, 500]   # Below
```

## Workflow Connections

Connect nodes to define the flow:

```python
# Basic connection
connect_nodes(
    workflow_id="xxx",
    source_node_id="node-1",
    target_node_id="node-2"
)

# Connect specific output/input
connect_nodes(
    workflow_id="xxx",
    source_node_id="if-node",
    target_node_id="true-branch",
    source_output_index=0  # Use output 0 (true branch)
)
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `N8N_API_URL` | Yes | `http://localhost:5678/api/v1` | Your n8n API endpoint |
| `N8N_API_KEY` | Yes | - | Your n8n API key |
| `N8N_MCP_PORT` | No | `8000` | HTTP server port |
| `N8N_MCP_HOST` | No | `localhost` | HTTP server host |

## Troubleshooting

### Server not starting

- Verify your `.env` file has correct `N8N_API_URL` and `N8N_API_KEY`
- Check that your n8n instance is accessible
- Ensure n8n API access is enabled (Settings > API)

### Tools not showing up

- Restart the MCP server after code changes
- Re-add the server to Claude Code: `claude mcp remove n8n` then `claude mcp add ...`
- Check server logs for errors

### Connection errors

- Verify `N8N_API_URL` includes `/api/v1` at the end
- Check your n8n API key has sufficient permissions
- Ensure network connectivity to your n8n instance

## Project Structure

```
n8n-mw/
├── n8n_server.py          # Main MCP server (47 tools)
├── n8n_mcp_server.py      # Alternative stdio version
├── n8n_http_server.py     # Alternative HTTP version
├── requirements.txt       # Python dependencies
├── .env                  # Environment configuration (create this)
├── .env.example          # Example environment file
├── .mcp.json            # MCP configuration (auto-generated)
├── README.md            # This file
└── venv/                # Virtual environment (created by you)
```

## License

MIT

## Contributing

Contributions welcome! Feel free to submit issues or pull requests.

## Related

- [n8n Documentation](https://docs.n8n.io/)
- [n8n API Reference](https://docs.n8n.io/api/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/PrefectHQ/fastmcp)
