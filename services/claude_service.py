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

def _layer_prompt(layer: str, layer_desc: str) -> str:
    return f"""Generate nodes for the "{layer}" layer of a CS tech learning graph.

Layer: {layer_desc}

Output exactly 18 nodes. Each node:
- id: slug (e.g. "react")
- label: display name
- layer: "{layer}"
- description: max 8 words
- related_ids: 2-4 ids of OTHER nodes in THIS response only
- aliases: 0-1 items max

Also output edges array: [{{"source":"a","target":"b","weight":1.0}}] — only between nodes in THIS response, max 25 edges.

Respond with ONLY valid JSON, no markdown:
{{"nodes":[...],"edges":[...]}}"""


def generate_initial_graph() -> OceanGraph:
    layers = [
        ("surface",   "Core web frontend: HTML, CSS, JavaScript, TypeScript, React, Vue, Angular, Svelte, WebAssembly, browser APIs, web animations, accessibility"),
        ("mid",       "Backend frameworks and protocols: Node.js, FastAPI, Django, Express, gRPC, REST, GraphQL, WebSockets, OAuth, JWT, message queues (Redis, RabbitMQ, Kafka)"),
        ("deep_mid",  "Databases, networking, OS, algorithms: PostgreSQL, MySQL, MongoDB, Redis, TCP/IP, DNS, HTTP, Linux, data structures, algorithms, computer architecture, security fundamentals, cryptography"),
        ("deep",      "Infra, DevOps, AI/ML, systems: Docker, Kubernetes, Terraform, AWS, GCP, CI/CD, Git, Nginx, PyTorch, TensorFlow, LLMs, Rust, Go, C++, compilers, distributed systems, observability"),
    ]

    all_nodes: list[dict] = []
    all_edges: list[dict] = []

    for layer_id, layer_desc in layers:
        prompt = _layer_prompt(layer_id, layer_desc)
        message = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        data = _extract_json(raw)
        all_nodes.extend(data.get("nodes", []))
        all_edges.extend(data.get("edges", []))
        print(f"  Layer '{layer_id}': {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges")

    # Validate related_ids
    node_ids = {n["id"] for n in all_nodes}
    for node in all_nodes:
        node["related_ids"] = [r for r in node.get("related_ids", []) if r in node_ids]
    # Validate edges
    all_edges = [e for e in all_edges if e["source"] in node_ids and e["target"] in node_ids]
    # Deduplicate edges
    seen_edges: set[tuple] = set()
    deduped_edges = []
    for e in all_edges:
        key = (min(e["source"], e["target"]), max(e["source"], e["target"]))
        if key not in seen_edges:
            seen_edges.add(key)
            deduped_edges.append(e)

    return OceanGraph.model_validate({
        "version": "1.0.0",
        "nodes": all_nodes,
        "edges": deduped_edges,
        "generated_at": datetime.utcnow().isoformat(),
    })


# ---------------------------------------------------------------------------
# (b) Learning Tree Generation
# ---------------------------------------------------------------------------

def _learning_tree_prompt(node_id: str, node_label: str) -> str:
    return f"""Learning tree for "{node_label}" (id: "{node_id}").

Output exactly 10 nodes. Levels: 0=mastery, 1=advanced, 2=intermediate, 3=beginner.
Each node: id, label (max 4 words), description (max 8 words), level, parent_id (null for root), resources (exactly 2 items).
Resource: title (max 6 words), url (real working URL from MDN/freeCodeCamp/official docs/YouTube), type (video|article|docs|course|book), is_free (bool).

root id must be "{node_id}-mastery".

Respond with ONLY valid compact JSON:
{{"root_node_id":"{node_id}-mastery","nodes":[...],"generated_at":"2026-01-01T00:00:00"}}"""


def generate_learning_tree(node_id: str, node_label: str) -> LearningTree:
    message = client.messages.create(
        model=MODEL,
        max_tokens=8192,
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
    # Keep prompt small: cap inputs
    unmatched_str = ", ".join(unmatched[:10])
    existing_str = ", ".join(existing_node_ids[:50])
    return f"""Classify these unrecognized CS technologies: {unmatched_str}

For each, output: id (slug), label, layer (surface|mid|deep_mid|deep), description (max 8 words), suggested_parent_id (closest from: {existing_str}), scope (major|niche).

Respond ONLY with compact JSON:
{{"proposals":[{{"id":"x","label":"X","layer":"mid","description":"x","suggested_parent_id":"y","scope":"niche"}}]}}"""


def propose_new_nodes(unmatched_names: list[str], existing_node_ids: list[str]) -> list[NodeProposal]:
    if not unmatched_names:
        return []
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": _proposal_prompt(unmatched_names, existing_node_ids)}],
    )
    raw = message.content[0].text
    data = _extract_json(raw)
    return [NodeProposal.model_validate(item) for item in data.get("proposals", [])]
