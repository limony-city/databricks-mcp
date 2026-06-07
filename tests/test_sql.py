"""
Tests for the SQL API and the corresponding MCP tools.
"""

import importlib.util
from unittest.mock import AsyncMock, patch

import pytest

if importlib.util.find_spec("mcp") is None:  # pragma: no cover - environment guard
    pytest.skip("mcp package not available", allow_module_level=True)

from databricks_mcp.api import sql
from databricks_mcp.server.databricks_mcp_server import DatabricksMCPServer


@pytest.mark.asyncio
async def test_execute_statement_defaults_to_50s_wait_timeout():
    """The bumped synchronous wait window catches most queries inline."""
    with patch("databricks_mcp.api.sql.make_api_request", new=AsyncMock(return_value={})) as mock:
        await sql.execute_statement(statement="SELECT 1", warehouse_id="wh-1")

    body = mock.call_args.kwargs["data"]
    assert body["wait_timeout"] == "50s"
    assert body["statement"] == "SELECT 1"
    assert body["warehouse_id"] == "wh-1"


@pytest.mark.asyncio
async def test_execute_statement_honors_explicit_wait_timeout():
    """Callers can override the wait window (e.g. '0s' for fire-and-poll flows)."""
    with patch("databricks_mcp.api.sql.make_api_request", new=AsyncMock(return_value={})) as mock:
        await sql.execute_statement(
            statement="SELECT 1",
            warehouse_id="wh-1",
            wait_timeout="0s",
        )

    assert mock.call_args.kwargs["data"]["wait_timeout"] == "0s"


@pytest.mark.asyncio
async def test_get_statement_status_calls_correct_endpoint():
    with patch("databricks_mcp.api.sql.make_api_request", new=AsyncMock(return_value={})) as mock:
        await sql.get_statement_status("01abc")

    method, path = mock.call_args.args[0], mock.call_args.args[1]
    assert method == "GET"
    assert path == "/api/2.0/sql/statements/01abc"


@pytest.mark.asyncio
async def test_cancel_statement_calls_correct_endpoint():
    with patch("databricks_mcp.api.sql.make_api_request", new=AsyncMock(return_value={})) as mock:
        await sql.cancel_statement("01abc")

    method, path = mock.call_args.args[0], mock.call_args.args[1]
    assert method == "POST"
    assert path == "/api/2.0/sql/statements/01abc/cancel"


@pytest.mark.asyncio
async def test_new_sql_tools_are_registered():
    """execute_sql gained a wait_timeout arg; polling/cancel tools are exposed."""
    server = DatabricksMCPServer()
    tools = {tool.name: tool for tool in await server.list_tools()}

    assert "execute_sql" in tools
    assert "wait_timeout" in tools["execute_sql"].inputSchema["properties"]

    assert "get_statement_status" in tools
    assert "statement_id" in tools["get_statement_status"].inputSchema["properties"]

    assert "cancel_statement" in tools
    assert "statement_id" in tools["cancel_statement"].inputSchema["properties"]
