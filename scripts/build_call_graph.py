import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_symbols(index_dir: Path):
    symbols_path = index_dir / "symbols.json"
    if not symbols_path.is_file():
        raise FileNotFoundError(f"Symbol index not found: {symbols_path}")
    return json.loads(symbols_path.read_text(encoding="utf-8"))


def build_symbol_lookup(symbols):
    """Index symbols by qualified name and simple name."""
    by_qualified_name = {}
    by_name = defaultdict(list)
    for symbol in symbols:
        by_qualified_name[symbol["qualified_name"]] = symbol
        by_name[symbol["symbol"]].append(symbol)
    return by_qualified_name, by_name


def resolve_call(call_name, caller, by_qualified_name, by_name):
    """Resolve a call when confidence is reasonable; otherwise return None."""
    if call_name in by_qualified_name:
        return call_name

    matches = [
        qualified_name for qualified_name in by_qualified_name
        if qualified_name.endswith(f".{call_name}")
    ]
    if len(matches) == 1:
        return matches[0]

    candidates = by_name.get(call_name, [])
    if len(candidates) == 1:
        return candidates[0]["qualified_name"]
    return None


def main(index_dir: Path):
    index_dir = index_dir.expanduser().resolve()
    symbols = load_symbols(index_dir)
    by_qualified_name, by_name = build_symbol_lookup(symbols)
    graph = []

    for symbol in symbols:
        if symbol["symbol_type"] not in {"function", "async_function"}:
            continue
        for call in symbol.get("calls", []):
            target = resolve_call(
                call["name"], symbol, by_qualified_name, by_name
            )
            target_symbol = by_qualified_name.get(target) if target else None
            graph.append({
                "caller": symbol["qualified_name"],
                "caller_file": symbol["file_path"],
                "line": call["line"],
                "call_name": call["name"],
                "resolved_target": target,
                "target_file": target_symbol["file_path"] if target_symbol else None,
                "target_start_line": target_symbol["start_line"] if target_symbol else None,
                "target_end_line": target_symbol["end_line"] if target_symbol else None,
                "resolution_status": "resolved" if target_symbol else "unresolved",
            })

    output_path = index_dir / "call_graph.json"
    output_path.write_text(
        json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    resolved = sum(edge["resolution_status"] == "resolved" for edge in graph)
    print(f"Call edges: {len(graph)}")
    print(f"Resolved: {resolved}")
    print(f"Unresolved: {len(graph) - resolved}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a static call graph from symbols.json."
    )
    parser.add_argument(
        "--index-dir", type=Path, default=Path.cwd() / ".code_index",
        help="Directory containing symbols.json and receiving call_graph.json.",
    )
    args = parser.parse_args()
    main(args.index_dir)
