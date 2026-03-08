"""FastMCP Todo server: create, list, update, delete tasks."""

from datetime import datetime, timezone
from typing import Literal

from fastmcp import FastMCP

mcp = FastMCP("todo_server")

# In-memory store (single process). For multi-process use a shared store.
_tasks: list[dict] = []
_task_id_counter = 0


def _next_id() -> int:
    global _task_id_counter
    _task_id_counter += 1
    return _task_id_counter


@mcp.tool()
def create_task(title: str, description: str = "") -> str:
    """Create a new todo task. Returns the new task id and title."""
    task_id = _next_id()
    task = {
        "id": task_id,
        "title": title,
        "description": description,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }
    _tasks.append(task)
    return f"Created task {task_id}: {title}"


@mcp.tool()
def list_tasks(status_filter: Literal["open", "done", "all"] = "all") -> str:
    """List todo tasks. status_filter: 'open', 'done', or 'all'."""
    if status_filter == "all":
        out = _tasks
    else:
        out = [t for t in _tasks if t["status"] == status_filter]
    if not out:
        return "No tasks found."
    lines = []
    for t in out:
        lines.append(f"ID {t['id']}: {t['title']} [{t['status']}]")
    return "\n".join(lines)


@mcp.tool()
def update_task(task_id: int, title: str | None = None, status: Literal["open", "done"] | None = None) -> str:
    """Update a task's title and/or status. Use task_id from list_tasks."""
    for t in _tasks:
        if t["id"] == task_id:
            if title is not None:
                t["title"] = title
            if status is not None:
                t["status"] = status
                if status == "done":
                    t["completed_at"] = datetime.now(timezone.utc).isoformat()
                else:
                    t["completed_at"] = None
            return f"Updated task {task_id}."
    return f"Task {task_id} not found."


@mcp.tool()
def delete_task(task_id: int) -> str:
    """Delete a task by id. Use task_id from list_tasks."""
    for i, t in enumerate(_tasks):
        if t["id"] == task_id:
            _tasks.pop(i)
            return f"Deleted task {task_id}."
    return f"Task {task_id} not found."


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
        path="/mcp",
    )
