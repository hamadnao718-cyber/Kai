#!/usr/bin/env python3
"""
OpenManus MCP Server — HTTP transport wrapper for Kai integration.

This server exposes OpenManus tools (bash, browser, file editor) over
Streamable HTTP so Kai can discover and call them as native MCP tools.

Usage:
    python mcp_server.py [--host 0.0.0.0] [--port 8765]

Environment variables (override config.toml values):
    OPENMANUS_API_KEY       LLM API key
    OPENMANUS_API_BASE_URL  LLM base URL  (default: https://api.openai.com/v1)
    OPENMANUS_MODEL         LLM model ID  (default: gpt-4o)
    OPENMANUS_HOST          Bind host     (default: 0.0.0.0)
    OPENMANUS_PORT          Bind port     (default: 8765)
"""

import argparse
import asyncio
import atexit
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stderr)])

# ---------------------------------------------------------------------------
# Bootstrap: write a config.toml from env vars before importing OpenManus so
# that app.config picks up the correct LLM credentials at import time.
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).parent / "config"
_CONFIG_PATH = _CONFIG_DIR / "config.toml"


def _bootstrap_config() -> None:
    """Write config/config.toml from environment variables if not already present."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("OPENMANUS_API_KEY", "")
    base_url = os.environ.get("OPENMANUS_API_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENMANUS_MODEL", "gpt-4o")

    if not _CONFIG_PATH.exists() and api_key:
        content = f"""[llm]
model = "{model}"
base_url = "{base_url}"
api_key = "{api_key}"
max_tokens = 4096
temperature = 0.0

[llm.vision]
model = "{model}"
base_url = "{base_url}"
api_key = "{api_key}"
max_tokens = 4096
temperature = 0.0
"""
        _CONFIG_PATH.write_text(content)
        logging.info("Wrote config/config.toml from environment variables.")


_bootstrap_config()

# Add the OpenManus package root to sys.path so imports resolve correctly when
# this script is run from inside the openmanus/ subdirectory.
_PKG_ROOT = Path(__file__).parent / "src"
if _PKG_ROOT.exists():
    sys.path.insert(0, str(_PKG_ROOT))

# ---------------------------------------------------------------------------
# OpenManus imports
# ---------------------------------------------------------------------------

from app.tool.base import BaseTool  # noqa: E402
from app.tool.bash import Bash  # noqa: E402
from app.tool.browser_use_tool import BrowserUseTool  # noqa: E402
from app.tool.str_replace_editor import StrReplaceEditor  # noqa: E402
from app.tool.terminate import Terminate  # noqa: E402
from app.logger import logger  # noqa: E402

from inspect import Parameter, Signature
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP  # noqa: E402


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------


class OpenManusMCPServer:
    """OpenManus MCP server with Streamable HTTP transport for Kai."""

    def __init__(self, name: str = "openmanus") -> None:
        self.server = FastMCP(name)
        self.tools: Dict[str, BaseTool] = {
            "bash": Bash(),
            "browser": BrowserUseTool(),
            "editor": StrReplaceEditor(),
            "terminate": Terminate(),
        }

    # ------------------------------------------------------------------
    # Tool registration helpers (adapted from app/mcp/server.py)
    # ------------------------------------------------------------------

    def _build_docstring(self, tool_function: dict) -> str:
        description = tool_function.get("description", "")
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])
        docstring = description
        if param_props:
            docstring += "\n\nParameters:\n"
            for param_name, param_details in param_props.items():
                required_str = "(required)" if param_name in required_params else "(optional)"
                param_type = param_details.get("type", "any")
                param_desc = param_details.get("description", "")
                docstring += f"    {param_name} ({param_type}) {required_str}: {param_desc}\n"
        return docstring

    def _build_signature(self, tool_function: dict) -> Signature:
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])
        parameters = []
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        for param_name, param_details in param_props.items():
            annotation = type_map.get(param_details.get("type", ""), Any)
            default = Parameter.empty if param_name in required_params else None
            parameters.append(
                Parameter(
                    name=param_name,
                    kind=Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
            )
        return Signature(parameters=parameters)

    def _register_tool(self, tool: BaseTool, method_name: Optional[str] = None) -> None:
        tool_name = method_name or tool.name
        tool_param = tool.to_param()
        tool_function = tool_param["function"]

        async def tool_method(**kwargs):
            logger.info(f"Executing {tool_name}: {kwargs}")
            result = await tool.execute(**kwargs)
            logger.info(f"Result of {tool_name}: {result}")
            if hasattr(result, "model_dump"):
                return json.dumps(result.model_dump())
            elif isinstance(result, dict):
                return json.dumps(result)
            return result

        tool_method.__name__ = tool_name
        tool_method.__doc__ = self._build_docstring(tool_function)
        tool_method.__signature__ = self._build_signature(tool_function)

        self.server.tool()(tool_method)
        logger.info(f"Registered tool: {tool_name}")

    def _register_all_tools(self) -> None:
        for tool in self.tools.values():
            self._register_tool(tool)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        logger.info("Cleaning up OpenManus MCP server resources")
        if "browser" in self.tools and hasattr(self.tools["browser"], "cleanup"):
            await self.tools["browser"].cleanup()

    def run(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        """Register tools and start the Streamable HTTP server."""
        self._register_all_tools()
        atexit.register(lambda: asyncio.run(self.cleanup()))
        logger.info(f"Starting OpenManus MCP server on http://{host}:{port}/mcp")
        self.server.run(transport="streamable-http", host=host, port=port, path="/mcp")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenManus MCP Server (Streamable HTTP — for Kai integration)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("OPENMANUS_HOST", "0.0.0.0"),
        help="Bind host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("OPENMANUS_PORT", "8765")),
        help="Bind port (default: 8765)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    server = OpenManusMCPServer()
    server.run(host=args.host, port=args.port)
