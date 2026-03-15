import json
import os
from datetime import datetime
from filelock import FileLock
from models.graph_models import OceanGraph

GRAPH_PATH = os.getenv("GRAPH_STORE_PATH", "data/graph_data.json")
LOCK_PATH = GRAPH_PATH + ".lock"

# In-memory cache: (version, graph)
_cache: tuple[str, OceanGraph] | None = None


def read_graph() -> OceanGraph | None:
    global _cache
    if not os.path.exists(GRAPH_PATH):
        return None
    try:
        with open(GRAPH_PATH, "r") as f:
            raw = f.read().strip()
        if not raw:
            return None
        data = json.loads(raw)
        graph = OceanGraph.model_validate(data)
        _cache = (graph.version, graph)
        return graph
    except Exception:
        return None


def write_graph(graph: OceanGraph) -> None:
    global _cache
    with FileLock(LOCK_PATH):
        os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
        with open(GRAPH_PATH, "w") as f:
            json.dump(graph.model_dump(), f, indent=2)
    _cache = (graph.version, graph)


def bump_version(graph: OceanGraph) -> OceanGraph:
    """Increment patch version e.g. 1.0.3 -> 1.0.4"""
    parts = graph.version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return graph.model_copy(update={"version": ".".join(parts), "generated_at": datetime.utcnow().isoformat()})
