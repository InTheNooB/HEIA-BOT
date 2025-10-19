#!/usr/bin/env python3
import argparse
import json

# Folder names to delete (case-insensitive)
# Folder names to delete (lowercase, normalized)
SKIP_NAMES = {
    "resume",
    "cheat_sheet",
    "tp",
    "tps",
    "tp_series",
    "projet_integre",
    "projet",
    "wortschatz",
    "exercices_moodle",
    "Exercice_moodle",
    "exos simulation matlab",  # normalized (catch both %20 and space)
    "code",
    "applications_mobiles",
    "pi",
    "rs",  # temporary
    "il",  # temporary
    "quizz",
    "wiki",
}

# Old exam years to delete (as substrings)
OLD_YEARS = [
    "2003",
    "2004",
    "2005",
    "2006",
    "2007",
    "2008",
    "2009",
    "2010",
    "2011",
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018",
    "2019",
    "2020",
    "0405",
    "0506",
    "0607",
    "0708",
    "0809",
    "0910",
    "1011",
    "1112",
    "1213",
    "1314",
    "1415",
    "1516",
    "1617",
    "1718",
    "1819",
    "1920",
    "2122",
    "README",
]


def should_skip(node_name):
    """Return True if this node should be deleted."""
    if not node_name:
        return False

    name = node_name.lower().replace("%20", " ")

    # Skip if folder matches SKIP_NAMES (match whole name, case insensitive)
    for skip in SKIP_NAMES:
        if name == skip.lower():
            return True

    # Skip if old year pattern appears in name
    for year in OLD_YEARS:
        if year in name:
            return True

    return False


def filter_node(node):
    """Recursively filter out unwanted folders or old exams."""
    name = node.get("name", "")
    if should_skip(name):
        return None

    filtered = {"name": node.get("name"), "path": node.get("path")}

    if "children" in node and isinstance(node["children"], list):
        kept_children = []
        for child in node["children"]:
            filtered_child = filter_node(child)
            if filtered_child is not None:
                kept_children.append(filtered_child)
        if kept_children:
            filtered["children"] = kept_children

    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="Filter out unwanted folders and old exams from tree JSON."
    )
    parser.add_argument(
        "--infile", default="tree_simplified.json", help="Input JSON file"
    )
    parser.add_argument(
        "--outfile", default="tree_filtered.json", help="Output JSON file"
    )
    args = parser.parse_args()

    with open(args.infile, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered = filter_node(data)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    print(f"✅ Filtered tree written to {args.outfile}")


if __name__ == "__main__":
    main()
