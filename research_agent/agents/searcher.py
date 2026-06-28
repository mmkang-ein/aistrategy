# agents/searcher.py
# Stage 2: 웹 검색 (병렬) — Anthropic web_search tool 활용

import asyncio
import anthropic
from config.settings import ANTHROPIC_API_KEY, MODEL_WORKER, SearchConfig
from core.base_agent import BaseAgent
from core.logger import get_logger

logger = get_logger("SearcherAgent")


class SearcherAgent(BaseAgent):
    def __init__(self, mode: str, cfg: SearchConfig, verbose: bool = False):
        super().__init__("SearcherAgent", MODEL_WORKER, verbose)
        self.mode = mode
        self.cfg  = cfg

    async def _search_one(self, query: str, idx: int) -> dict:
        """단일 쿼리 웹 검색"""
        self.print_status(f"검색 [{idx+1}]: {query[:60]}")
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    tools=[{"type": "web_search_20250305", "name": "web_search"}],
                    messages=[{
                        "role": "user",
                        "content": (
                            f"다음 주제로 최신 자료를 검색하고 핵심 내용을 요약해주세요.\n"
                            f"주제: {query}\n"
                            f"모드: {'학술 논문 위주' if self.mode == 'academic' else 'AI 전략·트렌드 위주'}\n"
                            f"결과를 한국어로 요약해주세요."
                        )
                    }]
                )
            )
            # 텍스트 블록 추출
            text_parts = [
                block.text for block in response.content
                if hasattr(block, "text")
            ]
            content = "\n".join(text_parts)
            return {
                "query":   query,
                "content": content,
                "status":  "success",
            }
        except Exception as e:
            logger.warning(f"검색 실패 [{query}]: {e}")
            return {"query": query, "content": "", "status": "error", "error": str(e)}

    async def search_parallel(self, queries: list[str], max_papers: int) -> list[dict]:
        """여러 쿼리를 병렬 실행, max_parallel 제한 적용"""
        queries = queries[:self.cfg.max_parallel_queries]
        semaphore = asyncio.Semaphore(self.cfg.max_parallel_queries)

        async def bounded_search(query, idx):
            async with semaphore:
                return await self._search_one(query, idx)

        tasks = [bounded_search(q, i) for i, q in enumerate(queries)]
        results = await asyncio.gather(*tasks)
        success = [r for r in results if r["status"] == "success"]
        self.logger.info(f"검색 완료: {len(success)}/{len(queries)}건 성공")
        return success
