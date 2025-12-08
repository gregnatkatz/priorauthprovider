"""
Azure Functions MCP Server for Denial Intelligence Platform
Exposes 42+ AI agents as MCP tools for Azure AI Foundry Agent Service
"""
import azure.functions as func
import json
import logging
import os
from typing import Any, Dict, List, Optional
from azure.identity import DefaultAzureCredential
from tools.agent_tools import AgentToolRegistry, execute_agent_tool

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the agent tool registry
tool_registry = AgentToolRegistry()


@app.route(route="mcp", methods=["GET", "POST"])
async def mcp_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main MCP endpoint that handles tool discovery and execution.
    
    GET: Returns list of available tools (tool discovery)
    POST: Executes a specific tool
    """
    try:
        if req.method == "GET":
            return await handle_tool_discovery(req)
        elif req.method == "POST":
            return await handle_tool_execution(req)
        else:
            return func.HttpResponse(
                json.dumps({"error": "Method not allowed"}),
                status_code=405,
                mimetype="application/json"
            )
    except Exception as e:
        logger.error(f"MCP endpoint error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


async def handle_tool_discovery(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle MCP tool discovery request.
    Returns the list of all available agent tools with their schemas.
    """
    tools = tool_registry.get_all_tools()
    
    response = {
        "jsonrpc": "2.0",
        "result": {
            "tools": tools,
            "serverInfo": {
                "name": "denial-intelligence-mcp-server",
                "version": "1.0.0",
                "description": "MCP server exposing 42+ AI agents for denial management"
            }
        }
    }
    
    return func.HttpResponse(
        json.dumps(response),
        status_code=200,
        mimetype="application/json"
    )


async def handle_tool_execution(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle MCP tool execution request.
    Executes the specified agent tool with provided arguments.
    """
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )
    
    tool_name = body.get("name")
    arguments = body.get("arguments", {})
    
    if not tool_name:
        return func.HttpResponse(
            json.dumps({"error": "Tool name is required"}),
            status_code=400,
            mimetype="application/json"
        )
    
    if not tool_registry.tool_exists(tool_name):
        return func.HttpResponse(
            json.dumps({"error": f"Tool '{tool_name}' not found"}),
            status_code=404,
            mimetype="application/json"
        )
    
    result = await execute_agent_tool(tool_name, arguments)
    
    response = {
        "jsonrpc": "2.0",
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result) if isinstance(result, dict) else str(result)
                }
            ]
        }
    }
    
    return func.HttpResponse(
        json.dumps(response),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="mcp/tools", methods=["GET"])
async def list_tools(req: func.HttpRequest) -> func.HttpResponse:
    """
    List all available MCP tools.
    """
    tools = tool_registry.get_all_tools()
    return func.HttpResponse(
        json.dumps({"tools": tools, "count": len(tools)}),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="mcp/tools/{tool_name}", methods=["GET"])
async def get_tool(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get details for a specific tool.
    """
    tool_name = req.route_params.get("tool_name")
    tool = tool_registry.get_tool(tool_name)
    
    if not tool:
        return func.HttpResponse(
            json.dumps({"error": f"Tool '{tool_name}' not found"}),
            status_code=404,
            mimetype="application/json"
        )
    
    return func.HttpResponse(
        json.dumps(tool),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="mcp/execute", methods=["POST"])
async def execute_tool(req: func.HttpRequest) -> func.HttpResponse:
    """
    Execute a specific MCP tool.
    """
    return await handle_tool_execution(req)


@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint.
    """
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "denial-intelligence-mcp-server",
            "version": "1.0.0",
            "agents_available": len(tool_registry.get_all_tools())
        }),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="mcp/categories", methods=["GET"])
async def list_categories(req: func.HttpRequest) -> func.HttpResponse:
    """
    List all agent categories.
    """
    categories = tool_registry.get_categories()
    return func.HttpResponse(
        json.dumps({"categories": categories}),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="mcp/categories/{category}", methods=["GET"])
async def get_tools_by_category(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get all tools in a specific category.
    """
    category = req.route_params.get("category")
    tools = tool_registry.get_tools_by_category(category)
    return func.HttpResponse(
        json.dumps({"category": category, "tools": tools, "count": len(tools)}),
        status_code=200,
        mimetype="application/json"
    )
