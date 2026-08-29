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
def get_disk_usage(service: str) -> dict:
    """Return current disk usage for a service, if it tracks disk metrics."""
    return ops.get_disk_usage(service)


@mcp.tool()
def restart_service(service: str) -> dict:
    """Restart a service."""
    return ops.restart_service(service)


@mcp.tool()
def clear_old_logs(service: str) -> dict:
    """Purge old logs on a service to free disk space."""
    return ops.clear_old_logs(service)


if __name__ == "__main__":
    mcp.run()