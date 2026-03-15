from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.graph_models import OceanGraph
from services import graph_store, claude_service

router = APIRouter(prefix="/api")


class InitRequest(BaseModel):
    force: bool = False


@router.get("/graph", response_model=OceanGraph)
def get_graph():
    graph = graph_store.read_graph()
    if graph is None:
        raise HTTPException(status_code=404, detail={"needs_init": True, "message": "Graph not initialized"})
    return graph


@router.post("/graph/initialize", response_model=OceanGraph)
def initialize_graph(body: InitRequest = InitRequest()):
    existing = graph_store.read_graph()
    if existing and not body.force:
        return existing

    graph = claude_service.generate_initial_graph()
    graph_store.write_graph(graph)
    return graph
