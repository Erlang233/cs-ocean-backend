import json
import os
import re
from datetime import datetime

import anthropic
from models.graph_models import OceanGraph, OceanNode, OceanEdge
from models.tree_models import LearningTree, TreeNode, Resource
from models.scan_models import DetectedTech, NodeProposal

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def _extract_json(text: str) -> dict | list:
    """Extract JSON from a Claude response that may contain markdown fences."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# (a) Graph Generation
# ---------------------------------------------------------------------------

GRAPH_GENERATION_PROMPT = """Generate a comprehensive CS technology ocean graph for a self-learning website.

Requirements:
- Include exactly 100 nodes covering: web frontend, web backend, databases, networking,
  OS fundamentals, cloud/devops, AI/ML, mobile, systems programming, security
- Assign each node one of these layers: "surface" | "mid" | "deep_mid" | "deep"
  - "surface": core web frontend (HTML, CSS, JavaScript, TypeScript, React, Vue, Angular, etc.)
  - "mid": backend frameworks, APIs, protocols (Node.js, FastAPI, Django, REST, GraphQL, gRPC, etc.)
  - "deep_mid": databases, networking, OS, data structures, algorithms, security fundamentals
  - "deep": infra, DevOps, AI/ML, systems programming (Docker, Kubernetes, Terraform, PyTorch, Rust, Go, etc.)
- For each node include:
  - id: lowercase slug (e.g. "react", "postgresql", "kubernetes")
  - label: proper display name (e.g. "React", "PostgreSQL", "Kubernetes")
  - layer: one of surface/mid/deep_mid/deep
  - description: 1 sentence explaining what this technology is
  - related_ids: list of 3-8 IDs of other nodes in this graph that are closely related
  - aliases: list of common alternative names/spellings (may be empty)
- Include an edges array as [{source, target, weight}] pairs
  - weight 1.0 = normal relation, 1.5 = very closely related, 0.7 = loosely related
  - Each node should appear in at least 2 edges
- Ensure the graph is well-connected (no isolated nodes)
- version: "1.0.0"

Respond with ONLY valid JSON — no explanation, no markdown fences:
{
  "version": "1.0.0",
  "nodes": [...],
  "edges": [...],
  "generated_at": "<ISO timestamp>"
}"""


def generate_initial_graph() -> OceanGraph:
    message = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": GRAPH_GENERATION_PROMPT}],
    )
    raw = message.content[0].text
    data = _extract_json(raw)

    # Validate: ensure all related_ids reference real node IDs
    node_ids = {n["id"] for n in data["nodes"]}
    for node in data["nodes"]:
        node["related_ids"] = [r for r in node.get("related_ids", []) if r in node_ids]

    if "generated_at" not in data or not data["generated_at"]:
        data["generated_at"] = datetime.utcnow().isoformat()

    return OceanGraph.model_validate(data)


# ---------------------------------------------------------------------------
# (b) Learning Tree Generation
# ---------------------------------------------------------------------------

def _learning_tree_prompt(node_id: str, node_label: str) -> str:
    return f"""Generate a structured learning tree for the technology: "{node_label}" (id: "{node_id}").

Requirements:
- The tree has one root node representing mastery of {node_label} (level=0)
- Leaf nodes represent the most basic prerequisites a complete beginner needs (level=3 or 4)
- Include 12-20 nodes total, organized into 3-5 levels:
  - Level 0: mastery (root node, id = "{node_id}-mastery")
  - Level 1: advanced topics
  - Level 2: intermediate topics
  - Level 3: beginner foundations
  - Level 4: absolute prerequisites (optional, for complex topics)
- Each node:
  - id: unique slug (e.g. "{node_id}-basics", "{node_id}-advanced-patterns")
  - label: short display name
  - description: 1-2 sentences on what you learn at this stage
  - level: integer 0-4
  - parent_id: id of parent node (null for root)
  - resources: 3-5 learning resources
    - title: resource name
    - url: actual URL (prefer MDN, freeCodeCamp, official docs, YouTube, roadmap.sh)
    - type: "video" | "article" | "docs" | "course" | "book"
    - is_free: boolean

Respond with ONLY valid JSON:
{{
  "root_node_id": "{node_id}-mastery",
  "nodes": [...],
  "generated_at": "<ISO timestamp>"
}}"""


def generate_learning_tree(node_id: str, node_label: str) -> LearningTree:
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": _learning_tree_prompt(node_id, node_label)}],
    )
    raw = message.content[0].text
    data = _extract_json(raw)
    if "generated_at" not in data or not data["generated_at"]:
        data["generated_at"] = datetime.utcnow().isoformat()
    return LearningTree.model_validate(data)


# ---------------------------------------------------------------------------
# (c) Repo Scanning — Pass 1: detect tech
# ---------------------------------------------------------------------------

def _scan_prompt(repo_url: str, files: dict[str, str], known_node_ids: list[str]) -> str:
    file_sections = "\n\n".join(
        f"<{filename}>\n{content}\n</{filename}>"
        for filename, content in files.items()
    )
    known_ids_str = ", ".join(known_node_ids[:150])  # cap to avoid token overrun
    return f"""Analyze these files from the GitHub repository "{repo_url}" and identify all technologies used.

{file_sections}

Identify every framework, library, language, tool, database, and infrastructure technology present.
For each detected technology:
- name: canonical technology name (e.g. "React", "PostgreSQL", "Docker")
- confidence: 0.0-1.0 (1.0 if explicitly declared, 0.7 if inferred from patterns)
- matched_node_id: best matching ID from this list, or null if no match:
  [{known_ids_str}]

Rules for matching:
- Match by name similarity (e.g. "React" -> "react", "PostgreSQL" -> "postgresql")
- If unsure, set matched_node_id to null
- Only include technologies with confidence >= 0.5

Respond with ONLY valid JSON:
{{"detected": [{{"name": "...", "matched_node_id": "..." , "confidence": 0.9}}]}}"""


def detect_tech_stack(repo_url: str, files: dict[str, str], known_node_ids: list[str]) -> list[DetectedTech]:
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": _scan_prompt(repo_url, files, known_node_ids)}],
    )
    raw = message.content[0].text
    data = _extract_json(raw)
    return [DetectedTech.model_validate(item) for item in data.get("detected", [])]


# ---------------------------------------------------------------------------
# (d) New Node Detection — Pass 2: classify unmatched tech
# ---------------------------------------------------------------------------

def _proposal_prompt(unmatched: list[str], existing_node_ids: list[str]) -> str:
    existing_str = ", ".join(existing_node_ids[:150])
    unmatched_str = ", ".join(unmatched)
    return f"""The following technologies were detected in a repo scan but are NOT yet in our CS learning graph:
{unmatched_str}

For each technology, determine:
1. scope: "major" (widely-used technology worth a top-level graph node) or "niche" (specific library/tool better as a subtopic)
2. layer: "surface" | "mid" | "deep_mid" | "deep"
3. If scope="major": propose a new graph node
4. If scope="niche": identify the closest existing parent node from this list: [{existing_str}]

For each proposal:
- id: lowercase slug
- label: proper display name
- layer: one of surface/mid/deep_mid/deep
- description: 1 sentence
- suggested_parent_id: closest existing node id (required for niche, optional for major)
- scope: "major" or "niche"

Respond with ONLY valid JSON:
{{"proposals": [{{"id": "...", "label": "...", "layer": "...", "description": "...", "suggested_parent_id": "...", "scope": "..."}}]}}"""


def propose_new_nodes(unmatched_names: list[str], existing_node_ids: list[str]) -> list[NodeProposal]:
    if not unmatched_names:
        return []
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": _proposal_prompt(unmatched_names, existing_node_ids)}],
    )
    raw = message.content[0].text
    data = _extract_json(raw)
    return [NodeProposal.model_validate(item) for item in data.get("proposals", [])]
