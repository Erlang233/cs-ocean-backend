from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from models.tree_models import Resource


class PlanNode(BaseModel):
    id: str
    label: str
    description: str
    level: int  # 0=goal, 1=major area, 2=subtopic, 3=task
    parent_id: Optional[str] = None
    tech_ref: Optional[str] = None  # OceanGraph node id
    resources: list[Resource] = []


class ProjectLearningPlan(BaseModel):
    repo_url: str
    repo_name: str
    summary: str
    root_node_id: str
    nodes: list[PlanNode]
    generated_at: str


class DeepScanRequest(BaseModel):
    github_url: str
