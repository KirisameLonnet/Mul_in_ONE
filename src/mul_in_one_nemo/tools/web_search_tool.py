"""NeMo Agent Toolkit tool: WebSearch.

Provides a structured tool for web searching and optional fetching of result pages.
"""

import re
import logging
from typing import List, Optional, AsyncGenerator, Tuple

import httpx
from pydantic import BaseModel, Field, AnyUrl

from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

logger = logging.getLogger(__name__)


# Internal helper functions for web search
DDG_HTML_SEARCH = "https://duckduckgo.com/html/?q={query}"


async def _web_search(query: str, top_k: int = 5, timeout: float = 8.0) -> List[Tuple[str, str]]:
    """Perform a lightweight web search via DuckDuckGo HTML endpoint.

    Returns a list of (title, url) pairs.
    """
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "MulInOne/1.0"}) as client:
        r = await client.get(DDG_HTML_SEARCH.format(query=httpx.QueryParams({"q": query})))
        html = r.text
    # very lightweight parse: extract results from <a class="result__a" href="...">Title</a>
    results: List[Tuple[str, str]] = []
    for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL):
        url = m.group(1)
        title = re.sub(r"<[^>]+>", "", m.group(2))
        results.append((title.strip(), url.strip()))
        if len(results) >= top_k:
            break
    return results


async def _web_fetch(url: str, timeout: float = 8.0, max_chars: int = 5000) -> str:
    """Fetch page content and return a cleaned text snippet."""
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "MulInOne/1.0"}) as client:
        r = await client.get(url, follow_redirects=True)
        text = r.text
    # strip scripts/styles and tags
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query string")
    top_k: int = Field(default=3, ge=1, le=8, description="Max number of search results")
    fetch_snippets: bool = Field(default=True, description="Whether to fetch page snippets for top results")


class WebSearchResult(BaseModel):
    title: str = Field(...)
    url: AnyUrl = Field(...)
    snippet: Optional[str] = Field(default=None)


class WebSearchOutput(BaseModel):
    results: List[WebSearchResult] = Field(default_factory=list)


class WebSearchToolConfig(FunctionBaseConfig, name="web_search_tool"):
    max_fetch_chars: int = Field(default=1200, ge=256, le=10000)
    timeout_s: float = Field(default=8.0, ge=2.0, le=30.0)


@register_function(config_type=WebSearchToolConfig)
async def web_search_tool(config: WebSearchToolConfig, builder):  # builder present for NAT contract
    async def _single(input_data: WebSearchInput) -> WebSearchOutput:
        try:
            pairs = await _web_search(input_data.query, top_k=input_data.top_k, timeout=config.timeout_s)
            out: List[WebSearchResult] = []
            for title, url in pairs:
                snippet = None
                if input_data.fetch_snippets:
                    try:
                        snippet = (await _web_fetch(url, timeout=config.timeout_s, max_chars=config.max_fetch_chars))
                    except Exception:
                        pass
                out.append(WebSearchResult(title=title, url=url, snippet=snippet))
            return WebSearchOutput(results=out)
        except Exception as e:
            logger.error("WebSearchTool failed: %s", e)
            return WebSearchOutput(results=[])

    async def _stream(input_data: WebSearchInput) -> AsyncGenerator[WebSearchOutput, None]:
        # Simple one-shot; stream emits a single chunk
        yield await _single(input_data)

    try:
        yield FunctionInfo.create(
            single_fn=_single,
            stream_fn=_stream,
            input_schema=WebSearchInput,
            single_output_schema=WebSearchOutput,
            stream_output_schema=WebSearchOutput,
            description="搜索互联网获取最新公开信息（如新闻、价格、版本号、事实核查等）。返回相关网页的标题、链接和摘要，可用于引用外部来源。",
        )
    finally:
        pass
