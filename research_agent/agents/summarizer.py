# agents/summarizer.py
# Stage 2: 수집 자료 요약·분류

import asyncio
from core.base_agent import BaseAgent
from config.settings import MODEL_WORKER

SYSTEM = """당신은 학술·전략 문서 요약 전문가입니다.
주어진 텍스트에서 핵심 정보를 추출하여 JSON으로 반환하세요.
반드시 JSON만 반환하세요."""

PROMPT = """다음 텍스트를 요약하세요:

{content}

JSON 형식:
{{
  "title": "핵심 주제",
  "key_findings": ["발견1", "발견2", "발견3"],
  "relevance": "연구 주제와의 관련성 (높음/중간/낮음)",
  "summary": "3-4문장 요약"
}}"""


class SummarizerAgent(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("SummarizerAgent", MODEL_WORKER, verbose)

    async def _summarize_one(self, item: dict) -> dict:
        content = item.get("content", "")[:3000]  # 토큰 절약
        if not content:
            return {**item, "summary_data": {}}
        response = await self.call_llm(SYSTEM, PROMPT.format(content=content), temperature=0.3)
        return {**item, "summary_data": self.parse_json(response)}

    async def summarize_all(self, items: list[dict]) -> list[dict]:
        self.print_status(f"{len(items)}건 병렬 요약 중...")
        tasks = [self._summarize_one(item) for item in items]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r.get("summary_data")]
