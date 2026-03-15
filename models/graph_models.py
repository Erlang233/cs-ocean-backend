from enum import Enum
from pydantic import BaseModel


class LayerDepth(str, Enum):
    SURFACE = "surface"    # HTML, CSS, JS, React, Vue, TypeScript
    MID = "mid"            # REST, GraphQL, Node.js, FastAPI, gRPC
    DEEP_MID = "deep_mid"  # Databases, Networking, OS fundamentals
    DEEP = "deep"          # AI/ML, Docker, K8s, Terraform, CI/CD


class OceanNode(BaseModel):
    id: str                      # slug: "react", "postgresql", "kubernetes"
    label: str                   # display name: "React", "PostgreSQL"
    layer: LayerDepth
    description: str             # 1-2 sentence summary
    related_ids: list[str] = []  # connected node IDs
    aliases: list[str] = []      # ["ReactJS", "react.js"] for fuzzy matching
    is_ai_proposed: bool = False


class OceanEdge(BaseModel):
    source: str
    target: str
    weight: float = 1.0


class OceanGraph(BaseModel):
    version: str
    nodes: list[OceanNode]
    edges: list[OceanEdge]
    generated_at: str
