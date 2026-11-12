"""Actual FastMCP stdio facade. Importing this module starts no service."""
from typing import Annotated, Any

if __package__:
    from .offline_facade import TOOLS, check_csv_grid as _check_csv_grid
else:
    from offline_facade import TOOLS, check_csv_grid as _check_csv_grid


def create_server():
    # Optional SDK is imported only for explicit server creation.
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
    from pydantic import Field

    # Keep SDK numeric coercion from erasing the facade's original-type guard.
    # An actual JSON integer remains a valid number; bool/string/container do not.
    # Annotations are evaluated here (not postponed) so the SDK sees Field metadata.
    def check_csv_grid(csv_path: str, time_column: str,
                       interval: Annotated[float, Field(strict=True)],
                       start: Annotated[float, Field(strict=True)],
                       end: Annotated[float, Field(strict=True)],
                       time_abs_tolerance: Annotated[float, Field(strict=True)],
                       numeric_columns: list[str] | None = None) -> dict[str, Any]:
        """Check a caller CSV grid using strict JSON numbers; no native calculation."""
        return _check_csv_grid(csv_path, time_column, interval, start, end,
                               time_abs_tolerance, numeric_columns)

    server = FastMCP("aspen-dynamics-offline-tools")
    for function in TOOLS:
        entry = check_csv_grid if function.__name__ == 'check_csv_grid' else function
        server.add_tool(entry, annotations=ToolAnnotations(readOnlyHint=True,
                                                            destructiveHint=False,
                                                            openWorldHint=False),
                        structured_output=True)
    return server


def main():
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
