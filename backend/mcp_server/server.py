from fastmcp import FastMCP
from process.mock_ops import tools as ops

mcp = FastMCP()

@mcp.tool()
def get_logs(service: str, minutes: int = 15) -> list[str]:
    """Return recent log lines for a service."""
    return ops.get_logs(service, minutes)


@mcp.tool()
def get_metrics(service: str) -> dict:
    """Return a current metrics snapshot for a service."""
    return ops.get_metrics(service)


@mcp.tool()
def restart_service(service: str) -> dict:
    """Restart a service."""
    return ops.restart_service(service)


if __name__ == "__main__":
    mcp.run()  