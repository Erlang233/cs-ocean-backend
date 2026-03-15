from typing import Literal
from pydantic import BaseModel


class Resource(BaseModel):
    title: str
    url: str
    type: Literal["video", "article", "docs", "course", "book"]
    is_free: bool


class TreeNode(BaseModel):
    id: str
    label: str
    description: str        # what you learn at this stage
    level: int              # 0 = root (mastery), higher = more beginner
    parent_id: str | None   # None for root
    resources: list[Resource] = []


class LearningTree(BaseModel):
    root_node_id: str       # the technology clicked
    nodes: list[TreeNode]
    generated_at: str
