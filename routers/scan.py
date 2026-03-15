from fastapi import APIRouter, HTTPException
from models.scan_models import ScanRequest, ScanResult
from services import claude_service, github_service, node_matcher, graph_store

router = APIRouter(prefix="/api")


@router.post("/scan/github", response_model=ScanResult)
async def scan_github(body: ScanRequest):
    graph = graph_store.read_graph()
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    # Fetch repo files
    try:
        files = await github_service.fetch_repo_files(body.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not files:
        raise HTTPException(status_code=422, detail="No recognizable config files found in repository")

    known_ids = [n.id for n in graph.nodes]

    # Pass 1: detect tech stack
    detected = claude_service.detect_tech_stack(body.github_url, files, known_ids)

    # Refine matches using alias lookup
    detected = node_matcher.match_to_graph(detected, graph)

    matched_ids = [t.matched_node_id for t in detected if t.matched_node_id]

    # Pass 2: propose new nodes for unmatched tech
    unmatched_names = [t.name for t in detected if t.matched_node_id is None]
    proposals = claude_service.propose_new_nodes(unmatched_names, known_ids)

    return ScanResult(
        repo_url=body.github_url,
        detected_techs=detected,
        matched_node_ids=list(set(matched_ids)),
        proposals=proposals,
        files_analyzed=list(files.keys()),
    )
