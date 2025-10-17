#!/usr/bin/env python3
import argparse
import json
import os


def collect_files(node, out_set):
    """Recursively collect paths that look like actual files (have an extension)."""
    path = node.get("path")
    children = node.get("children", [])

    # if no children and filename has an extension -> file
    if not children and path and os.path.splitext(path)[1]:
        out_set.add(path)
        return

    # recurse into children
    for child in children:
        collect_files(child, out_set)


def main():
    parser = argparse.ArgumentParser(
        description="Extract only real file paths (with extensions) from a tree JSON."
    )
    parser.add_argument(
        "--infile", default="tree_filtered.json", help="Input JSON file"
    )
    parser.add_argument("--outfile", default="files.json", help="Output JSON file")
    args = parser.parse_args()

    with open(args.infile, "r", encoding="utf-8") as f:
        data = json.load(f)

    files = set()
    collect_files(data, files)

    # sort alphabetically
    sorted_files = sorted(files)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(sorted_files, f, ensure_ascii=False, indent=2)

    print(f"✅ Extracted {len(sorted_files)} files into {args.outfile}")


if __name__ == "__main__":
    main()
