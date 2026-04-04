"""
Tree-Sitter AST API — Java & C++ parser via FastAPI.
Designed for extension to additional languages.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from app.analysis.tree_sitter_registry import get_tree_sitter_parser
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from tree_sitter import Node

# ---------------------------------------------------------------------------
# Language Registry — one place to add new languages later
# ---------------------------------------------------------------------------

class SupportedLanguage(str, Enum):
    java = "java"
    cpp = "cpp"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    code: str = Field(..., description="Source code to parse", min_length=1)
    language: SupportedLanguage = Field(..., description="Target language")
    include_text: bool = Field(
        default=False,
        description="Include the source text for each node (increases payload size)",
    )
    max_depth: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Limit AST traversal depth (None = unlimited)",
    )


class ASTNode(BaseModel):
    type: str
    start_byte: int
    end_byte: int
    start_point: tuple[int, int]   # (row, column)
    end_point: tuple[int, int]
    is_named: bool
    text: str | None = None
    children: list["ASTNode"] = []


class ParseResponse(BaseModel):
    language: str
    node_count: int
    parse_time_ms: float
    has_errors: bool
    tree: ASTNode


class HealthResponse(BaseModel):
    status: str
    supported_languages: list[str]


# ---------------------------------------------------------------------------
# AST Serialisation
# ---------------------------------------------------------------------------

def _node_to_dict(
    node: Node,
    source: bytes,
    include_text: bool,
    max_depth: int | None,
    current_depth: int = 0,
) -> ASTNode:
    """Recursively convert a tree-sitter Node to ASTNode."""
    text = source[node.start_byte : node.end_byte].decode("utf-8", errors="replace") if include_text else None

    children: list[ASTNode] = []
    if max_depth is None or current_depth < max_depth:
        for child in node.children:
            children.append(
                _node_to_dict(child, source, include_text, max_depth, current_depth + 1)
            )

    return ASTNode(
        type=node.type,
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        start_point=node.start_point,
        end_point=node.end_point,
        is_named=node.is_named,
        text=text,
        children=children,
    )


def _count_nodes(node: Node) -> int:
    """Count all nodes in the tree."""
    return 1 + sum(_count_nodes(c) for c in node.children)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Tree-Sitter AST API",
    description="Parse Java and C++ source code into Abstract Syntax Trees using Tree-Sitter.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        supported_languages=[lang.value for lang in SupportedLanguage],
    )


@app.post("/parse", response_model=ParseResponse, tags=["AST"])
def parse(request: ParseRequest) -> ParseResponse:
    """
    Parse source code and return a full AST.

    - **code**: The raw source code string.
    - **language**: `java` or `cpp`.
    - **include_text**: Attach the source snippet for every node.
    - **max_depth**: Cap tree depth for large files.
    """
    parser = get_tree_sitter_parser(request.language.value)
    source = request.code.encode("utf-8")

    t0 = time.perf_counter()
    tree = parser.parse(source)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    root = tree.root_node
    if root is None:
        raise HTTPException(status_code=422, detail="Tree-Sitter returned an empty tree.")

    ast = _node_to_dict(root, source, request.include_text, request.max_depth)
    node_count = _count_nodes(root)

    return ParseResponse(
        language=request.language.value,
        node_count=node_count,
        parse_time_ms=round(elapsed_ms, 3),
        has_errors=root.has_error,
        tree=ast,
    )


@app.get("/languages", tags=["Meta"])
def list_languages() -> dict[str, Any]:
    """List all supported languages and their metadata."""
    return {
        "languages": [
            {"id": lang.value, "display_name": lang.value.upper()}
            for lang in SupportedLanguage
        ]
    }
