# agents/reference_builder.py
# 수집 자료 기반 참고문헌 자동 생성 (APA / IEEE)

import re

from core.base_agent import BaseAgent
from config.settings import MODEL_WORKER

_URL_RE = re.compile(r"https?://\S+")


def _dedupe_by_url(refs: list) -> list:
    """참고문헌 문자열에서 URL을 추출해 완전히 같은 URL이 이미 나온 항목은 제거
    (첫 번째 등장한 항목만 유지). URL을 못 찾은 항목은 그대로 유지한다."""
    seen = set()
    result = []
    for r in refs:
        m = _URL_RE.search(r)
        if m:
            url = m.group(0).rstrip(").,]")
            if url in seen:
                continue
            seen.add(url)
        result.append(r)
    return result


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

    def _format_sources(self, summaries: list, queries: list, limit: int = 20) -> str:
        """각 URL마다 실제로 수집된 개별 title을 사용 (검색 쿼리 하나에 여러 URL이
        묶여 있다고 해서 그 URL들에 같은 제목을 붙이면 안 됨 — 서로 다른 문서임)."""
        lines = []
        for i, s in enumerate(summaries):
            sd = s.get("summary_data", {})
            summary = sd.get("summary", "")[:120]
            sources = s.get("sources", [])
            if sources:
                for src in sources[:3]:
                    url = src.get("url", "")
                    if not url:
                        continue
                    title = src.get("title") or sd.get("title") or "(제목 없음)"
                    lines.append(f"[{len(lines) + 1}] title: {title} | url: {url} | 요약: {summary}")
            else:
                query = s.get("query", queries[i] if i < len(queries) else "")
                title = sd.get("title") or query or "(제목 없음)"
                lines.append(f"[{len(lines) + 1}] title: {title} | url: (URL 없음) | 요약: {summary}")
            if len(lines) >= limit:
                break
        return "\n".join(lines) if lines else "자료 없음"

    async def build(self, summaries: list, queries: list) -> list[str]:
        self.print_status(f"참고문헌 생성 중 ({self.style} 형식, {len(summaries)}건)...")
        if not summaries:
            self.logger.warning("수집된 summaries가 없어 참고문헌을 생성하지 못함 (0건)")
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
        if not refs:
            self.logger.warning(
                "참고문헌이 0건 생성됨 — LLM 응답 JSON 파싱 실패 또는 빈 결과일 가능성 있음"
            )
        before = len(refs)
        refs = _dedupe_by_url(refs)
        if len(refs) < before:
            self.logger.warning(
                f"URL 기준 중복 참고문헌 {before - len(refs)}건 제거됨 "
                f"(모델이 프롬프트의 중복 제거 지시를 놓쳤을 가능성)"
            )
        self.logger.info(f"참고문헌 {len(refs)}건 생성 완료")
        return refs
