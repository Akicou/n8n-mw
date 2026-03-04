#!/usr/bin/env python3
"""Test script to verify n8n MCP server tools are working"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

if not os.getenv("N8N_API_KEY"):
    print("❌ N8N_API_KEY not found in .env file")
    exit(1)

print("✅ Environment variables loaded")
print(f"   N8N_API_URL: {os.getenv('N8N_API_URL')}")

# Test import
try:
    from n8n_mcp_server import mcp
    print("✅ n8n_mcp_server imported successfully")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    exit(1)

# List available tools
tools = mcp._tools
print(f"\n📋 Available MCP tools ({len(tools)}):")
for tool_name in tools:
    print(f"   - {tool_name}")

print("\n✅ Server is ready! Restart Claude Code to use the MCP tools.")
