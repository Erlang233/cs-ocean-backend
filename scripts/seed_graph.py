#!/usr/bin/env python3
"""
Run this locally to generate and save graph_data.json:
  cd cs-ocean-backend
  pip install -r requirements.txt
  ANTHROPIC_API_KEY=sk-ant-... python scripts/seed_graph.py

Then commit data/graph_data.json to the repo so Railway has it on deploy.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.claude_service import generate_initial_graph

if __name__ == "__main__":
    print("Generating CS ocean graph via Claude...")
    graph = generate_initial_graph()
    print(f"Generated {len(graph.nodes)} nodes and {len(graph.edges)} edges")

    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "graph_data.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(graph.model_dump(), f, indent=2)

    print(f"Saved to {output_path}")
    print("Now commit data/graph_data.json to the repo.")
