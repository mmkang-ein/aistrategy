# agents/writer.py
# Stage 6: 최종 문서 생성 (논문 초안 or 전략 리포트)

import json
from datetime import datetime
from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_ORCHESTRATOR, MAX_TOKENS_WRITER

SYSTEM_ACADEMIC = """당신은 컴퓨터비전·AI 분야 논문 작성 전문가입니다.
주어진 연구 내용을 바탕으로 학술 논문 초안을 Markdown으로 작성하세요."""

SYSTEM_STRATEGY = """당신은 AI 전략 컨설팅 리포트 작성 전문가입니다.
주어진 분석 내용을 바탕으로 전문적인 전략 리포트를 Markdown으로 작성하세요."""

WRITE_PROMPT_ACADEMIC = """
주제: {topic}
연구 계획: {plan}
핵심 발견: {findings}
선정 아이디어: {idea}
실험 설계: {experiment}
리뷰 요약: {review_summary}
생성 코드 여부: {has_code}

다음 구조로 논문 초안을 작성하세요 (Markdown):

# {topic}

## Abstract
(200자 이내)

## 1. Introduction
- 연구 배경 및 동기
- 핵심 기여 (Contributions)

## 2. Related Work
- 기존 연구 현황
- 본 연구와의 차별점

## 3. Methodology
- 제안 방법론 상세 설명
- 실험 설계

## 4. Experiments
- 데이터셋 및 평가 지표
- 예상 결과

## 5. Discussion
- 연구 의의
- 한계점 및 향후 연구

## 6. Conclusion

"""

WRITE_PROMPT_STRATEGY = """
주제: {topic}
연구 계획: {plan}
핵심 발견: {findings}
선정 분석 프레임: {idea}
검증 방법: {experiment}
리뷰 요약: {review_summary}

다음 구조로 AI 전략 리포트를 작성하세요 (Markdown):

# {topic} — AI 전략 분석 리포트

> 작성일: {date} | AI전략연구원

## Executive Summary
(300자 이내 핵심 요약)

## 1. 배경 및 분석 목적

## 2. 현황 분석
- 글로벌 동향
- 국내 현황

## 3. 핵심 이슈 및 기회

## 4. 전략적 시사점
- 단기 (6개월)
- 중기 (1-2년)
- 장기 (3-5년)

## 5. 권고사항

## 6. 결론

"""


class WriterAgent(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("WriterAgent", MODEL_ORCHESTRATOR, verbose)
        self.mode = mode
        self.system = SYSTEM_ACADEMIC if mode == "academic" else SYSTEM_STRATEGY

    def _format_findings(self, summaries: list) -> str:
        lines = []
        for s in summaries[:5]:
            sd = s.get("summary_data", {})
            lines.append(f"- {sd.get('title','')}: {sd.get('summary','')[:100]}")
        return "\n".join(lines)

    def _format_review_summary(self, reviews: list) -> str:
        if not reviews:
            return "리뷰 없음"
        last = reviews[-1]
        score = last.get("score", 0)
        feedback = last.get("feedback", "")[:300]
        return f"최종 점수: {score:.2f}\n피드백: {feedback}"

    async def write(self, state: ResearchState) -> str:
        self.print_status("최종 문서 작성 중...")
        findings = self._format_findings(state.summaries)
        review_summary = self._format_review_summary(state.reviews)

        if self.mode == "academic":
            prompt = WRITE_PROMPT_ACADEMIC.format(
                topic=state.topic,
                plan=json.dumps(state.plan, ensure_ascii=False)[:500],
                findings=findings,
                idea=json.dumps(state.selected_idea, ensure_ascii=False),
                experiment=json.dumps(state.experiment, ensure_ascii=False),
                review_summary=review_summary,
                has_code="예" if state.code_snippet else "아니오"
            )
        else:
            prompt = WRITE_PROMPT_STRATEGY.format(
                topic=state.topic,
                plan=json.dumps(state.plan, ensure_ascii=False)[:500],
                findings=findings,
                idea=json.dumps(state.selected_idea, ensure_ascii=False),
                experiment=json.dumps(state.experiment, ensure_ascii=False),
                review_summary=review_summary,
                date=datetime.now().strftime("%Y년 %m월 %d일")
            )

        document = await self.call_llm(
            self.system, prompt,
            max_tokens=MAX_TOKENS_WRITER,
            temperature=0.6
        )

        # 참고문헌 섹션 추가
        if state.references:
            style = "IEEE" if self.mode == "academic" else "APA"
            ref_header = f"\n\n## References ({style})\n\n"
            ref_lines = "\n\n".join(state.references)
            document += ref_header + ref_lines

        # 코드 첨부 (academic 모드)
        if self.mode == "academic" and state.code_snippet:
            document += f"\n\n## Appendix: Analysis Code\n\n```python\n{state.code_snippet}\n```"

        return document
