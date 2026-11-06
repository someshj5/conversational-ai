from pathlib import Path
from langchain.tools import tool
from src.forge_agent.code_search import search_symbol


def create_search_code_tool(index_dir: Path):
    index_dir = Path(index_dir).resolve()

    @tool("search_code")
    def search_code(query: str) -> str:
        """Search indexed symbols in the selected repository."""

        results = search_symbol(query, index_dir)

        if not results:
            return f"No indexed symbols found for query: {query!r}"

        formatted = [
            (
                f"Symbol: {item['qualified_name']}\n"
                f"File: {item['file_path']}\n"
                f"Lines: {item['start_line']}-{item['end_line']}\n"
                f"Signature: {item['signature']}"
            )
            for item in results[:20]
        ]

        output = "\n\n".join(formatted)

        if len(results) > 20:
            output += f"\n\nShowing 20 of {len(results)} matches."

        return output

    return search_code