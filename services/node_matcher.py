from models.graph_models import OceanGraph
from models.scan_models import DetectedTech


def match_to_graph(detected: list[DetectedTech], graph: OceanGraph) -> list[DetectedTech]:
    """Fill matched_node_id for each detected tech via slug or alias lookup."""
    slug_map = {node.id: node for node in graph.nodes}
    alias_map: dict[str, str] = {}
    for node in graph.nodes:
        for alias in node.aliases:
            alias_map[alias.lower()] = node.id

    results = []
    for tech in detected:
        name_lower = tech.name.lower()
        slug = name_lower.replace(" ", "-").replace(".", "")

        matched_id = (
            slug_map.get(slug, None) and slug
            or slug_map.get(name_lower.replace(" ", ""), None) and name_lower.replace(" ", "")
            or alias_map.get(name_lower)
        )

        results.append(DetectedTech(
            name=tech.name,
            matched_node_id=matched_id,
            confidence=tech.confidence,
        ))
    return results
