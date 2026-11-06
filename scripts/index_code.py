import argparse
import ast
import json
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules", ".code_index",
}


def get_signature(node):
    """Return a readable signature for a function or method."""
    try:
        return f"({ast.unparse(node.args)})"
    except Exception:
        return "()"


def extract_calls(node):
    """Extract raw function and method call expressions from an AST node."""
    calls = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        try:
            call_name = ast.unparse(child.func)
        except Exception:
            continue
        calls.append({"name": call_name, "line": child.lineno})
    return calls


def extract_symbols(file_path: Path, repo_root: Path):
    """Extract class/function symbols from one Python file."""
    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        print(f"Skipping {file_path}: {exc}")
        return []

    relative_path = file_path.relative_to(repo_root).as_posix()
    symbols = []

    def visit(node, parents=()):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            qualified_name = ".".join((*parents, node.name))
            if isinstance(node, ast.ClassDef):
                symbol_type, signature = "class", None
            else:
                symbol_type = (
                    "async_function" if isinstance(node, ast.AsyncFunctionDef)
                    else "function"
                )
                signature = get_signature(node)

            symbols.append({
                "symbol": node.name,
                "qualified_name": qualified_name,
                "symbol_type": symbol_type,
                "file_path": relative_path,
                "start_line": node.lineno,
                "end_line": node.end_lineno,
                "signature": signature,
                "docstring": ast.get_docstring(node),
                "source": ast.get_source_segment(source, node),
                "calls": extract_calls(node) if not isinstance(node, ast.ClassDef) else [],
            })
            next_parents = (*parents, node.name)
        else:
            next_parents = parents

        for child in ast.iter_child_nodes(node):
            visit(child, next_parents)

    visit(tree)
    return symbols


def main(repo_root: Path, output_dir: Path):
    repo_root = repo_root.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not repo_root.is_dir():
        raise NotADirectoryError(f"Repository directory not found: {repo_root}")

    all_symbols = []
    for file_path in repo_root.rglob("*.py"):
        relative_parts = file_path.relative_to(repo_root).parts
        if any(part in EXCLUDED_DIRS for part in relative_parts):
            continue
        try:
            all_symbols.extend(extract_symbols(file_path, repo_root))
        except (UnicodeDecodeError, OSError) as exc:
            print(f"Skipping {file_path}: {exc}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "symbols.json"
    output_path.write_text(
        json.dumps(all_symbols, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Indexed {len(all_symbols)} symbols")
    print(f"Saved index to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a Python AST symbol index.")
    parser.add_argument(
        "--repo-root", type=Path, default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Index output directory (default: <repo-root>/.code_index).",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.expanduser().resolve()
    output_dir = args.output_dir or (repo_root / ".code_index")
    main(repo_root, output_dir)
