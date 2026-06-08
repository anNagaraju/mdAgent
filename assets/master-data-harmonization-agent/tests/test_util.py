"""Unit tests for utility functions in util.py."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from unittest.mock import MagicMock
import pytest
from util import (
    enhance_tool_description,
    enhance_tool_name,
    _is_retryable_error,
    MCP_MAX_RESPONSE_CHARS,
)
import httpx


def _make_mock_tool(server_name: str, name: str, description: str = "A tool", fragment_name: str = None):
    t = MagicMock()
    t.server_name = server_name
    t.name = name
    t.description = description
    if fragment_name is not None:
        t.fragment_name = fragment_name
    else:
        # Remove fragment_name attribute so getattr falls back
        del t.fragment_name
    return t


# --- enhance_tool_description ---

def test_enhance_tool_description_with_server_name():
    """Should prefix description with server name in brackets."""
    tool = _make_mock_tool("my-server", "my_tool", "Does something")
    result = enhance_tool_description(tool)
    assert result.startswith("[my-server]")
    assert "Does something" in result


def test_enhance_tool_description_none_tool():
    """None tool should return empty string."""
    assert enhance_tool_description(None) == ""


def test_enhance_tool_description_with_fragment_name():
    """When fragment_name is set, it should be used instead of server_name."""
    tool = _make_mock_tool("full.server.name", "my_tool", "Does something", fragment_name="short-name")
    result = enhance_tool_description(tool)
    assert "[short-name]" in result


# --- enhance_tool_name ---

def test_enhance_tool_name_ord_id_format():
    """Should drop first two segments of ORD-style server names."""
    tool = _make_mock_tool("sap.mcpbuilder:apiResource:cost-center:v1", "list_cost_centers")
    result = enhance_tool_name(tool)
    assert "cost-center" in result
    assert "list_cost_centers" in result
    assert len(result) <= 64


def test_enhance_tool_name_simple_server():
    """Simple server names should be used as-is."""
    tool = _make_mock_tool("simple-server", "my_tool")
    result = enhance_tool_name(tool)
    assert "simple-server" in result
    assert "my_tool" in result


def test_enhance_tool_name_none_tool():
    """None tool should return empty string."""
    assert enhance_tool_name(None) == ""


def test_enhance_tool_name_truncates_long_names():
    """Very long names should be truncated to 64 chars with hash suffix."""
    long_server = "a" * 40
    long_tool = "b" * 40
    tool = _make_mock_tool(long_server, long_tool)
    result = enhance_tool_name(tool)
    assert len(result) <= 64


def test_enhance_tool_name_sanitizes_invalid_chars():
    """Dots and colons in server name should be replaced with underscores."""
    tool = _make_mock_tool("server.with.dots", "tool_name")
    result = enhance_tool_name(tool)
    assert "." not in result


# --- _is_retryable_error ---

def test_is_retryable_generic_exception():
    """Generic exceptions should be retryable."""
    assert _is_retryable_error(Exception("network error")) is True


def test_is_retryable_http_4xx_not_retryable():
    """HTTP 4xx errors should not be retryable."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    exc = httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_resp)
    assert _is_retryable_error(exc) is False


def test_is_retryable_http_5xx_is_retryable():
    """HTTP 5xx server errors should be retryable."""
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    exc = httpx.HTTPStatusError("Service unavailable", request=MagicMock(), response=mock_resp)
    assert _is_retryable_error(exc) is True


def test_mcp_max_response_chars_default():
    """MCP_MAX_RESPONSE_CHARS should be a positive integer."""
    assert MCP_MAX_RESPONSE_CHARS > 0
