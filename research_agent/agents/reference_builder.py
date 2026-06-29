# agents/reference_builder.py
# 수집 자료 기반 참고문헌 자동 생성 (APA / IEEE)

from core.base_agent import BaseAgent
from config.settings import MODEL_WORKER

SYSTEM = """당신은 학술 참고문헌 포매터입니다.
수집된 자료 정보를 기반으로 정확한 형식의 참고문헌 목록을 생성하세요.
JSON만 반환하세요."""

PROMPT = """다음 수집 자료들을 {style} 형식 참고문헌으로 변환하세요.

수집 자료:
{sources}

형식 예시:
{example}

규칙:
- 출처 정보가 불완전하면 수집된 정보로 최대한 추정하세요.
- 저자 불명 시 "Various Authors" 또는 기관명 사용
- 연도 불명 시 수집 연도 2026 사용
- URL이 있으면 반드시 포함
- 중복 항목은 제거하세요

JSON 형식:
{{
  "references": [
    "참고문헌 항목 1",
    "참고문헌 항목 2"
  ]
}}"""

_EXAMPLE = {
    "IEEE": (
        "[1] A. Author and B. Author, \"Title of article,\" "
        "Journal Name, vol. 10, no. 2, pp. 100–110, 2024. [Online]. "
        "Available: https://example.com"
    ),
    "APA": (
        "Author, A. A., & Author, B. B. (2024). Title of article. "
        "Journal Name, 10(2), 100–110. https://doi.org/..."
    ),
}


class ReferenceBuilder(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("ReferenceBuilder", MODEL_WORKER, verbose)
        self.style = "IEEE" if mode == "academic" else "APA"

    def _format_sources(self, summaries: list, queries: list) -> str:
        lines = []
        for i, s in enumerate(summaries[:12], 1):
            sd = s.get("summary_data", {})
            query = s.get("query", queries[i - 1] if i <= len(queries) else "")
            title = sd.get("title") or query
            summary = sd.get("summary", "")[:120]
            lines.append(f"[{i}] 제목/주제: {title} | 요약: {summary}")
        return "\n".join(lines) if lines else "자료 없음"

    async def build(self, summaries: list, queries: list) -> list[str]:
        self.print_status(f"참고문헌 생성 중 ({self.style} 형식, {len(summaries)}건)...")
        if not summaries:
            return []
        sources = self._format_sources(summaries, queries)
        prompt = PROMPT.format(
            style=self.style,
            sources=sources,
            example=_EXAMPLE[self.style],
        )
        response = await self.call_llm(SYSTEM, prompt, temperature=0.2)
        data = self.parse_json(response)
        refs = data.get("references", [])
        self.logger.info(f"참고문헌 {len(refs)}건 생성 완료")
        return refs
