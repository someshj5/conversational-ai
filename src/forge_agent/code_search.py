
import json
from pathlib import Path


def search_symbol(
    query: str,
    index_dir: Path,
) -> list[dict]:
    """Search symbols within a repository-specific index."""

    index_dir = Path(index_dir).resolve()
    index_path = index_dir / "symbols.json"

    if not index_path.is_file():
        raise FileNotFoundError(
            f"Symbol index not found: {index_path}"
        )

    symbols = json.loads(
        index_path.read_text(encoding="utf-8")
    )

    normalized_query = query.casefold()

    return [
        symbol
        for symbol in symbols
        if normalized_query in symbol["qualified_name"].casefold()
        or normalized_query in symbol["symbol"].casefold()
    ]
