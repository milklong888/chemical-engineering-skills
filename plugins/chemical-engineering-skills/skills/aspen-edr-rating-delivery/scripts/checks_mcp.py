"""Optional stdio MCP facade; uses the same read-only JSON functions as the CLI."""
from mcp.server.fastmcp import FastMCP
from engineering_checks import TOOLS

mcp = FastMCP('read-only-engineering-checks')
for name, function in TOOLS.items():
    mcp.add_tool(function, name=name, description=function.__doc__)

if __name__ == '__main__':
    mcp.run(transport='stdio')
