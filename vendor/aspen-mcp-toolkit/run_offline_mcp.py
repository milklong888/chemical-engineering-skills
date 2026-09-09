#!/usr/bin/env python3
"""Run the unchanged vendored stdio server without update checks or dotenv files.

This backend launcher does not open Aspen by itself. Model tools still require
their separate task authority and installed commercial software. It does not
edit a global MCP configuration or launch a desktop window.
"""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


def main() -> None:
    # Exact supported FastMCP 3.4.2 settings, verified in its installed source.
    os.environ['FASTMCP_CHECK_FOR_UPDATES'] = 'off'
    os.environ['FASTMCP_SHOW_SERVER_BANNER'] = 'false'
    os.environ['FASTMCP_ENV_FILE'] = os.devnull
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
    runpy.run_module('aspen_mcp.server', run_name='__main__')


if __name__ == '__main__':
    main()
