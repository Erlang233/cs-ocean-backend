import json
import os
from fastapi import APIRouter, HTTPException
from models.tree_models import LearningTree
from services import claude_service, graph_store

router = APIRouter(prefix="/api")

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREE_CACHE_PATH = os.getenv("TREE_CACHE_PATH") or os.path.join(_BASE_DIR, "data", "learning_trees_cache.json")


def _read_cache() -> dict:
    if not os.path.exists(TREE_CACHE_PATH):
        return {}
    try:
        with open(TREE_CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(TREE_CACHE_PATH), exist_ok=True)
    with open(TREE_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


@router.get("/nodes/{node_id}/tree", response_model=LearningTree)
def get_learning_tree(node_id: str):
    # Check cache first
    cache = _read_cache()
    if node_id in cache:
        return LearningTree.model_validate(cache[node_id])

    # Find node label from graph
    graph = graph_store.read_graph()
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    node = next((n for n in graph.nodes if n.id == node_id), None)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    tree = claude_service.generate_learning_tree(node_id, node.label)

    # Cache it
    cache[node_id] = tree.model_dump()
    _write_cache(cache)

    return tree
