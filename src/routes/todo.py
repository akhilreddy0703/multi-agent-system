"""Todo CRUD API: interact with FastMCP Todo server."""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastmcp import Client
from pydantic import BaseModel

from src.config import settings

router = APIRouter(prefix="/todos", tags=["todos"])


async def _call_todo_tool(name: str, arguments: dict[str, Any]) -> str:
    """Call a tool on the Todo MCP server."""
    client = Client(settings.todo_mcp_url)
    try:
        async with client:
            result = await client.call_tool(name, arguments)
            if hasattr(result, "__iter__") and not isinstance(result, (str, dict)):
                parts = list(result)
                if parts and hasattr(parts[0], "text"):
                    return parts[0].text
                if parts:
                    return str(parts[0])
            if hasattr(result, "data"):
                return str(result.data)
            return str(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Todo server error: {e}") from e


class CreateTaskBody(BaseModel):
    title: str
    description: str = ""


class UpdateTaskBody(BaseModel):
    title: str | None = None
    status: Literal["open", "done"] | None = None


@router.post("")
async def create_task(body: CreateTaskBody):
    """Create a new task."""
    msg = await _call_todo_tool(
        "create_task",
        {"title": body.title, "description": body.description or ""},
    )
    return {"message": msg}


@router.get("")
async def list_tasks(status: Literal["open", "done", "all"] = "all"):
    """List tasks, optionally filtered by status."""
    msg = await _call_todo_tool("list_tasks", {"status_filter": status})
    return {"tasks": msg, "status_filter": status}


@router.put("/{task_id:int}")
async def update_task(task_id: int, body: UpdateTaskBody):
    """Update a task's title and/or status."""
    args: dict[str, Any] = {"task_id": task_id}
    if body.title is not None:
        args["title"] = body.title
    if body.status is not None:
        args["status"] = body.status
    msg = await _call_todo_tool("update_task", args)
    return {"message": msg}


@router.delete("/{task_id:int}")
async def delete_task(task_id: int):
    """Delete a task by id."""
    msg = await _call_todo_tool("delete_task", {"task_id": task_id})
    return {"message": msg}
