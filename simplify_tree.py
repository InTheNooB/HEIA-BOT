#!/usr/bin/env python3
import argparse
import json


def simplify_node(node):
    """Keep only name, path, and children (recursively)."""
    simplified = {
        "name": node.get("name"),
        "path": node.get("path"),
    }
    if "children" in node and isinstance(node["children"], list):
        simplified["children"] = [simplify_node(c) for c in node["children"]]
    return simplified


def main():
    parser = argparse.ArgumentParser(
        description="Simplify a Nextcloud tree JSON (keep only name/path/children)."
    )
    parser.add_argument("--infile", default="tree.json", help="Input JSON file")
    parser.add_argument(
        "--outfile", default="tree_simplified.json", help="Output JSON file"
    )
    args = parser.parse_args()

    with open(args.infile, "r", encoding="utf-8") as f:
        data = json.load(f)

    simplified = simplify_node(data)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)

    print(f"✅ Simplified structure written to {args.outfile}")


if __name__ == "__main__":
    main()
