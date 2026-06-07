"""
Web search tool — uses DuckDuckGo (FREE, no API key needed).
"""
from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Returns top results with titles, URLs, and snippets.
    Use this when you need current information from the internet."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(f"• {r['title']}\n  {r['href']}\n  {r['body']}")
        if not results:
            return f"No results found for: {query}"
        return f"Search results for '{query}':\n\n" + "\n\n".join(results)
    except ImportError:
        return "❌ duckduckgo-search not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"❌ Search failed: {e}"
