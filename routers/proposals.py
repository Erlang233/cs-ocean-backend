from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.graph_models import OceanGraph, OceanNode, OceanEdge
from models.scan_models import NodeProposal
from services import graph_store

router = APIRouter(prefix="/api")


class RejectRequest(BaseModel):
    proposal_id: str


@router.post("/proposals/accept", response_model=OceanGraph)
def accept_proposal(proposal: NodeProposal):
    graph = graph_store.read_graph()
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    # Check for duplicate
    if any(n.id == proposal.id for n in graph.nodes):
        raise HTTPException(status_code=409, detail=f"Node '{proposal.id}' already exists")

    new_node = OceanNode(
        id=proposal.id,
        label=proposal.label,
        layer=proposal.layer,
        description=proposal.description,
        related_ids=[proposal.suggested_parent_id] if proposal.suggested_parent_id else [],
        aliases=[],
        is_ai_proposed=True,
    )

    new_edges = []
    if proposal.suggested_parent_id:
        # Link to parent
        new_edges.append(OceanEdge(source=proposal.id, target=proposal.suggested_parent_id, weight=1.0))
        # Update parent's related_ids
        for node in graph.nodes:
            if node.id == proposal.suggested_parent_id:
                node.related_ids.append(proposal.id)

    updated_graph = graph.model_copy(update={
        "nodes": graph.nodes + [new_node],
        "edges": graph.edges + new_edges,
    })
    updated_graph = graph_store.bump_version(updated_graph)
    graph_store.write_graph(updated_graph)
    return updated_graph


@router.post("/proposals/reject")
def reject_proposal(body: RejectRequest):
    # Stateless — just acknowledge
    return {"ok": True, "rejected": body.proposal_id}
