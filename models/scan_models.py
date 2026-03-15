from typing import Literal
from pydantic import BaseModel
from models.graph_models import LayerDepth


class ScanRequest(BaseModel):
    github_url: str


class DetectedTech(BaseModel):
    name: str
    matched_node_id: str | None
    confidence: float


class NodeProposal(BaseModel):
    id: str
    label: str
    layer: LayerDepth
    description: str
    suggested_parent_id: str | None  # for niche scope: parent node
    scope: Literal["major", "niche"]


class ScanResult(BaseModel):
    repo_url: str
    detected_techs: list[DetectedTech]
    matched_node_ids: list[str]
    proposals: list[NodeProposal]
    files_analyzed: list[str]
