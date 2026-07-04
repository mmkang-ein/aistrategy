# agents/reference_builder.py
# 수집 자료 기반 참고문헌 자동 생성 (APA / IEEE)

from core.base_agent import BaseAgent
from config.settings import MODEL_WORKER

SYSTEM = """당신은 학술 참고문헌 포매터입니다.
수집된 자료 정보를 기반으로 정확한 형식의 참고문헌 목록을 생성하세요.
JSON만 반환하세요."""

PROMPT = """다음 수집 자료들을 {style} 형식 참고문헌으로 변환하세요.

수집 자료 (title/url은 실제 검색 결과에서 수집된 값입니다. 반드시 그대로 사용하세요):
{sources}

형식 예시:
{example}

규칙:
- 저자명·학술지명·발행연도 등 실제로 주어지지 않은 정보는 절대로 지어내지 마세요.
- 저자를 알 수 없으면 이름을 만들지 말고, 대신 실제 title을 그대로 참고문헌 항목의 제목으로 쓰고
  "[Online]. Available: {{url}}" 형식으로 URL을 반드시 포함하세요.
- 연도를 알 수 없으면 "n.d." (no date)로 표기하세요. 임의의 연도를 지어내지 마세요.
- 권/호/페이지 번호 등 원문에 없는 숫자는 절대 만들어내지 마세요 — 없으면 생략하세요.
- URL이 있으면 반드시 포함하세요.
- 중복 항목(같은 url)은 제거하세요.

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
            sources = s.get("sources", [])
            urls = ", ".join(src["url"] for src in sources[:3] if src.get("url")) or "(URL 없음)"
            lines.append(
                f"[{i}] title: {title} | url: {urls} | 요약: {summary}"
            )
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
