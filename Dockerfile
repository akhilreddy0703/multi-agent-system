# Multi-Agent RAG: app runs with uv, no container build required for local run.
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .python-version ./
COPY src ./src
COPY data ./data
COPY README.md ./

# Install dependencies and project
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV MILVUS_URI="http://milvus-standalone:19530"
ENV TODO_MCP_URL="http://todo-mcp:8001/mcp"

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
