# agents/writer.py
# Stage 6: 섹션별 분할 생성 — 각 섹션 독립 LLM 호출로 완성도 향상

import json
from datetime import datetime
from typing import Callable, Optional
from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_ORCHESTRATOR, MAX_TOKENS_SECTION, MAX_TOKENS_SECTION_RETRY_CAP

SYSTEM_ACADEMIC = """당신은 컴퓨터비전·AI 분야 학술 논문 작성 전문가입니다 (NeurIPS/CVPR/ICML 기준).
주어진 섹션만 Markdown으로 작성하세요. 헤딩(##)부터 시작하세요. JSON 없이 순수 텍스트만 반환."""

SYSTEM_STRATEGY = """당신은 McKinsey·BCG급 AI 전략 컨설팅 리포트 작성 전문가입니다.
주어진 섹션만 Markdown으로 작성하세요. 헤딩(##)부터 시작하세요. JSON 없이 순수 텍스트만 반환."""

# ── 학술 논문 섹션 프롬프트 ─────────────────────────────────────

_ACADEMIC_ABSTRACT = """
주제: {topic}
선정 아이디어: {idea_title} — {idea_desc}
핵심 발견: {findings}
예상 기여: {contributions}

## Abstract 섹션을 작성하세요.
- 연구 배경과 문제 정의 (1-2문장)
- 제안 방법론 핵심 (1-2문장)
- 예상 결과 및 의의 (1-2문장)
- 전체 150-220 단어 이내
- 수식 금지, 서술형 단락으로 작성
"""

_ACADEMIC_INTRODUCTION = """
주제: {topic}
연구 전략: {strategy}
핵심 질문: {key_questions}
Abstract: {abstract}

사용 가능한 참고문헌 목록 (인용 시 반드시 아래 번호 중에서만 [n] 형식으로 사용):
{references}

## 1. Introduction 섹션을 작성하세요.
### 1.1 Motivation and Background
(연구 배경, 문제의 중요성, 기존 한계 2-3단락)
- 선행 연구를 언급할 때는 반드시 위 목록에 실제로 있는 번호로 [n] 형식으로 인용하세요.
- "[CITATION]"처럼 실제 번호가 아닌 placeholder 텍스트는 절대 사용하지 마세요.
- 목록에 적절한 근거가 없으면 인용 없이 서술하세요 (없는 근거를 지어내지 마세요).
### 1.2 Research Contributions
아래 형식으로 3개 이상의 기여점 목록:
- **Contribution 1**: ...
- **Contribution 2**: ...
- **Contribution 3**: ...
### 1.3 Paper Organization
(논문 구성 개요 1단락)
"""

_ACADEMIC_RELATED = """
주제: {topic}
수집된 선행 연구 요약:
{summaries}
선정 아이디어: {idea_title}

사용 가능한 참고문헌 목록 (인용 시 반드시 아래 번호 중에서만 [n] 형식으로 사용):
{references}

## 2. Related Work 섹션을 작성하세요.
- 각 선행 연구를 언급할 때는 반드시 위 목록에 실제로 있는 번호로 [n] 형식으로 인용하세요.
- "[CITATION]"처럼 실제 번호가 아닌 placeholder 텍스트는 절대 사용하지 마세요.
- 목록에 없는 연구는 지어내지 말고, 위 목록 범위 내에서만 구체적으로 비교·분석하세요.
### 2.1 [주요 연구 분야 1] (topic에 맞게 제목 설정)
(3-5개 관련 연구 언급, 각 연구 비교 분석)
### 2.2 [주요 연구 분야 2]
(3-5개 관련 연구)
### 2.3 Comparison with Proposed Approach
(기존 연구와 본 연구의 차별점 명확히 서술)
"""

_ACADEMIC_METHODOLOGY = """
주제: {topic}
선정 아이디어:
{idea_json}
실험 설계:
{experiment_json}

## 3. Methodology 섹션을 작성하세요.
### 3.1 Problem Formulation
(수식 표기를 사용한 문제 정의, 입력/출력 정의)
### 3.2 Proposed Method
(제안 방법론 상세 설명, 각 구성 요소 역할)
### 3.3 Algorithm / Architecture
(핵심 알고리즘 또는 아키텍처 설명, 텍스트 다이어그램 포함)
- 실제 프로그래밍 언어 소스 코드(Python 등)를 작성하지 마세요 — 코드는 별도 Appendix에
  이미 첨부되어 있으므로 여기서 다시 작성하면 안 됩니다.
- 알고리즘은 번호를 매긴 pseudocode 단계 또는 텍스트 박스 다이어그램으로만 표현하세요.
### 3.4 Training Strategy
(학습 전략, 손실 함수, 최적화 방법)
"""

_ACADEMIC_EXPERIMENTS = """
주제: {topic}
실험 설계: {experiment_json}
평가 지표: {metrics}
데이터셋: {datasets}
비교 테이블 (Markdown):
{tables}

## 4. Experiments 섹션을 작성하세요.
### 4.1 Experimental Setup
(데이터셋, 구현 환경, 하이퍼파라미터 상세)

### 4.2 Main Results

아래 테이블을 그대로 포함하고 결과를 분석하세요:
{model_comparison_table}

(테이블 분석 2-3단락: 제안 방법의 우수성, 각 지표별 해석)

### 4.3 Ablation Study

아래 테이블을 그대로 포함하세요:
{ablation_table}

(각 구성 요소의 기여도 분석)

### 4.4 Qualitative Analysis
(정성적 분석, 시각화 결과 설명 — "Figure 1 shows..." 형식 사용)
"""

_ACADEMIC_DISCUSSION = """
주제: {topic}
실험 결과 요약: {experiment_summary}
리뷰 피드백: {review_feedback}
방법론 핵심: {method_core}

## 5. Discussion 섹션을 작성하세요.
### 5.1 Analysis of Results
(실험 결과의 의미와 성능 향상 이유 분석)
### 5.2 Limitations
(현재 연구의 한계점 3가지 이상, 솔직하게 서술)
### 5.3 Broader Impact
(사회적·기술적 영향, 잠재적 응용 분야)
"""

_ACADEMIC_CONCLUSION = """
주제: {topic}
핵심 기여: {contributions}
주요 실험 결과: {key_results}
선정 아이디어: {idea_title}

## 6. Conclusion 섹션을 작성하세요.
반드시 아래 두 파트를 포함하세요:

### 6.1 Summary
(연구 전체 요약, 핵심 기여점 재강조, 최소 4문장 이상)

### 6.2 Future Work
다음 3가지 이상의 향후 연구 방향을 구체적으로 제시하세요:
1. **Direction 1**: (구체적인 후속 연구 방향)
2. **Direction 2**: ...
3. **Direction 3**: ...

전체 Conclusion은 300자 이상으로 상세하게 작성하세요.
"""

# ── 전략 리포트 섹션 프롬프트 ─────────────────────────────────

_STRATEGY_EXEC_SUMMARY = """
주제: {topic}
분석 전략: {strategy}
핵심 발견: {findings}

## Executive Summary 섹션을 작성하세요.
- 핵심 인사이트 3가지를 bullet point로 (각 2-3문장)
- 전체 200-300자 이내
- 의사결정자를 위한 명확한 시사점 포함
"""

_STRATEGY_BACKGROUND = """
주제: {topic}
분석 전략: {strategy}
핵심 질문: {key_questions}

## 1. 배경 및 분석 목적 섹션을 작성하세요.
### 1.1 분석 배경
### 1.2 핵심 분석 질문
### 1.3 분석 범위 및 방법론
"""

_STRATEGY_LANDSCAPE = """
주제: {topic}
수집 자료 요약:
{summaries}

## 2. 현황 분석 섹션을 작성하세요.
### 2.1 글로벌 동향
(주요 시장·기술·정책 트렌드, 데이터·수치 포함)
### 2.2 국내 현황
(한국 시장·기업·정부 동향)
### 2.3 주요 플레이어 분석

아래 포맷의 비교 테이블을 포함하세요:
| 기업/기관 | 전략 | 강점 | 약점 |
|---|---|---|---|
| ... | ... | ... | ... |
"""

_STRATEGY_ISSUES = """
주제: {topic}
현황 분석 요약: {landscape_summary}
핵심 질문: {key_questions}

## 3. 핵심 이슈 및 기회 섹션을 작성하세요.
### 3.1 주요 도전 과제
(3-5개 구체적 이슈)
### 3.2 전략적 기회
(3-5개 구체적 기회)
### 3.3 리스크 요인
"""

_STRATEGY_IMPLICATIONS = """
주제: {topic}
핵심 발견: {findings}
기회 및 이슈: {issues_summary}

## 4. 전략적 시사점 섹션을 작성하세요.
### 4.1 단기 전략 (0-6개월)
(즉시 실행 가능한 액션 아이템 3가지)
### 4.2 중기 전략 (6개월-2년)
(역량 구축 및 포지셔닝 방향 3가지)
### 4.3 장기 전략 (2년 이상)
(미래 비전 및 선도 방향 3가지)
"""

_STRATEGY_RECOMMENDATIONS = """
주제: {topic}
전략적 시사점: {implications_summary}
리뷰 피드백: {review_feedback}

## 5. 권고사항 섹션을 작성하세요.
우선순위 순으로 5가지 구체적 권고사항:
### 권고 1: [제목]
(배경, 실행 방법, 예상 효과)
### 권고 2-5: (동일 형식)

각 권고사항에 | KPI | 목표치 | 타임라인 | 담당 | 형식의 테이블 포함.
"""

_STRATEGY_CONCLUSION = """
주제: {topic}
핵심 권고사항 요약: {recommendations_summary}
분석 전략: {strategy}

## 6. 결론 섹션을 작성하세요.
반드시 아래 두 파트를 포함하세요:

### 6.1 종합 결론
(분석 전체 요약, 핵심 메시지 강조, 최소 4문장)

### 6.2 향후 모니터링 포인트
다음 3가지 이상의 향후 모니터링 방향:
1. **포인트 1**: (구체적인 모니터링 항목과 주기)
2. **포인트 2**: ...
3. **포인트 3**: ...

전체 결론은 300자 이상으로 작성하세요.
"""


class WriterAgent(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("WriterAgent", MODEL_ORCHESTRATOR, verbose)
        self.mode = mode
        self.system = SYSTEM_ACADEMIC if mode == "academic" else SYSTEM_STRATEGY

    # ── 공통 헬퍼 ───────────────────────────────────────────────

    def _numbered_refs(self, refs: list, limit: int = 15) -> str:
        """참고문헌 리스트를 [n] 접두어로 통일해 프롬프트에 넣을 문자열로 변환.
        LLM이 앞에 이미 붙인 번호는 제거하고, 실제 순서(state.references의 인덱스)로
        다시 매겨 최종 References 섹션과 항상 일치하도록 한다."""
        import re as _re
        if not refs:
            return "(참고문헌 없음 — 인용하지 말고 서술하세요)"
        lines = []
        for i, r in enumerate(refs[:limit], 1):
            clean = _re.sub(r"^\[\d+\]\s*", "", r.strip())
            lines.append(f"[{i}] {clean}")
        return "\n".join(lines)

    def _findings(self, summaries: list, n: int = 6) -> str:
        lines = []
        for s in summaries[:n]:
            sd = s.get("summary_data", {})
            lines.append(f"- {sd.get('title', '')}: {sd.get('summary', '')[:120]}")
        return "\n".join(lines) or "수집 자료 없음"

    def _review_feedback(self, reviews: list) -> str:
        if not reviews:
            return "없음"
        last = reviews[-1]
        return f"점수 {last.get('score', 0):.2f} — {last.get('feedback', '')[:300]}"

    def _tables_str(self, tables: dict) -> str:
        if not tables:
            return "(테이블 없음)"
        parts = []
        for name, md in tables.items():
            parts.append(f"**{name}**\n{md}")
        return "\n\n".join(parts)

    async def _write_section(self, prompt: str, section_name: str,
                              callback: Optional[Callable] = None) -> str:
        self.print_status(f"  섹션 생성: {section_name}...")
        content, stop_reason = await self.call_llm(
            self.system, prompt,
            max_tokens=MAX_TOKENS_SECTION,
            temperature=0.65,
            label=section_name,
            return_meta=True,
        )
        if stop_reason == "max_tokens":
            retry_tokens = min(MAX_TOKENS_SECTION * 2, MAX_TOKENS_SECTION_RETRY_CAP)
            self.logger.warning(
                f"[{section_name}] 잘림 감지 — max_tokens={retry_tokens}로 1회 재시도"
            )
            content, stop_reason = await self.call_llm(
                self.system, prompt,
                max_tokens=retry_tokens,
                temperature=0.65,
                label=f"{section_name} (retry)",
                return_meta=True,
            )
            if stop_reason == "max_tokens":
                self.logger.warning(
                    f"[{section_name}] 재시도에도 잘림 — 그대로 사용 (수동 확인 필요)"
                )
        if not content or len(content.strip()) < 30:
            self.logger.warning(
                f"[{section_name}] 내용이 비어있거나 매우 짧음 ({len(content or '')}자) — 확인 필요"
            )
        if callback:
            callback(section_name, content)
        self.print_status(f"  ✓ Section: {section_name} ({len(content)}자)")
        return content

    def _enforce_conclusion(self, text: str) -> str:
        """결론이 너무 짧으면 Future Work 텍스트를 보완"""
        if len(text) >= 200:
            return text
        supplement = (
            "\n\n### Future Work\n"
            "1. **Scale-up Experiments**: Extend evaluation to larger benchmarks.\n"
            "2. **Cross-domain Transfer**: Investigate generalization across domains.\n"
            "3. **Real-world Deployment**: Validate in production environments.\n"
        )
        return text + supplement

    # ── 학술 논문 작성 ──────────────────────────────────────────

    async def _write_academic(self, state: ResearchState,
                               callback: Optional[Callable]) -> str:
        idea = state.selected_idea
        idea_title = idea.get("title", state.topic)
        idea_desc  = idea.get("description", "")
        findings   = self._findings(state.summaries)
        review_fb  = self._review_feedback(state.reviews)
        plan       = state.plan
        tables     = state.experiment_tables
        exp        = state.experiment

        contribs = json.dumps(plan.get("expected_contributions", []), ensure_ascii=False)

        sections = {}

        # 1. Abstract
        s = await self._write_section(
            _ACADEMIC_ABSTRACT.format(
                topic=state.topic, idea_title=idea_title, idea_desc=idea_desc,
                findings=findings, contributions=contribs,
            ), "Abstract", callback)
        sections["abstract"] = s

        # 2. Introduction
        s = await self._write_section(
            _ACADEMIC_INTRODUCTION.format(
                topic=state.topic,
                strategy=plan.get("strategy", "")[:300],
                key_questions=json.dumps(plan.get("key_questions", []), ensure_ascii=False),
                abstract=sections["abstract"][:400],
                references=self._numbered_refs(state.references),
            ), "Introduction", callback)
        sections["introduction"] = s

        # 3. Related Work
        s = await self._write_section(
            _ACADEMIC_RELATED.format(
                topic=state.topic,
                summaries=self._findings(state.summaries, 8),
                idea_title=idea_title,
                references=self._numbered_refs(state.references),
            ), "Related Work", callback)
        sections["related_work"] = s

        # 4. Methodology
        s = await self._write_section(
            _ACADEMIC_METHODOLOGY.format(
                topic=state.topic,
                idea_json=json.dumps(idea, ensure_ascii=False)[:600],
                experiment_json=json.dumps(exp, ensure_ascii=False)[:400],
            ), "Methodology", callback)
        sections["methodology"] = s

        # 5. Experiments
        s = await self._write_section(
            _ACADEMIC_EXPERIMENTS.format(
                topic=state.topic,
                experiment_json=json.dumps(exp, ensure_ascii=False)[:400],
                metrics=", ".join(exp.get("metrics", ["Accuracy"])[:4]),
                datasets=", ".join(exp.get("datasets", ["TBD"])[:3]),
                tables=self._tables_str(tables),
                model_comparison_table=tables.get("model_comparison", "(테이블 없음)"),
                ablation_table=tables.get("ablation", "(테이블 없음)"),
            ), "Experiments", callback)
        sections["experiments"] = s

        # 6. Discussion
        s = await self._write_section(
            _ACADEMIC_DISCUSSION.format(
                topic=state.topic,
                experiment_summary=exp.get("expected_results", "")[:300],
                review_feedback=review_fb,
                method_core=idea.get("methodology", "")[:300],
            ), "Discussion", callback)
        sections["discussion"] = s

        # 7. Conclusion (강제 최소 길이)
        s = await self._write_section(
            _ACADEMIC_CONCLUSION.format(
                topic=state.topic,
                contributions=contribs,
                key_results=exp.get("expected_results", "")[:200],
                idea_title=idea_title,
            ), "Conclusion", callback)
        sections["conclusion"] = self._enforce_conclusion(s)

        state.section_documents = sections

        # 문서 조립
        doc = f"# {state.topic}\n\n"
        doc += sections["abstract"] + "\n\n"
        doc += sections["introduction"] + "\n\n"
        doc += sections["related_work"] + "\n\n"
        doc += sections["methodology"] + "\n\n"
        doc += sections["experiments"] + "\n\n"
        doc += sections["discussion"] + "\n\n"
        doc += sections["conclusion"] + "\n\n"

        # 안전장치: 지시를 따르지 않고 남은 [CITATION] placeholder가 있으면
        # 실제 인용인 것처럼 보이는 가짜 표기를 방지하기 위해 명확히 표시하고 로그 남김
        leftover = doc.count("[CITATION]")
        if leftover:
            self.logger.warning(
                f"[CITATION] placeholder {leftover}건이 실제 번호로 대체되지 않고 남음 — "
                f"[REF NEEDED]로 표시하여 출력함"
            )
            doc = doc.replace("[CITATION]", "[REF NEEDED]")

        # References
        if state.references:
            doc += f"## References (IEEE)\n\n"
            doc += "\n\n".join(state.references)

        # Appendix: code
        if state.code_snippet:
            doc += f"\n\n## Appendix: Analysis Code\n\n```python\n{state.code_snippet}\n```"

        return doc

    # ── 전략 리포트 작성 ────────────────────────────────────────

    async def _write_strategy(self, state: ResearchState,
                               callback: Optional[Callable]) -> str:
        plan     = state.plan
        findings = self._findings(state.summaries)
        review_fb = self._review_feedback(state.reviews)
        exp      = state.experiment
        tables   = state.experiment_tables

        sections = {}

        # Executive Summary
        s = await self._write_section(
            _STRATEGY_EXEC_SUMMARY.format(
                topic=state.topic,
                strategy=plan.get("strategy", "")[:300],
                findings=findings,
            ), "Executive Summary", callback)
        sections["exec_summary"] = s

        # Background
        s = await self._write_section(
            _STRATEGY_BACKGROUND.format(
                topic=state.topic,
                strategy=plan.get("strategy", "")[:300],
                key_questions=json.dumps(plan.get("key_questions", []), ensure_ascii=False),
            ), "Background", callback)
        sections["background"] = s

        # Landscape
        s = await self._write_section(
            _STRATEGY_LANDSCAPE.format(
                topic=state.topic,
                summaries=self._findings(state.summaries, 8),
            ), "Landscape Analysis", callback)
        sections["landscape"] = s

        # Issues
        s = await self._write_section(
            _STRATEGY_ISSUES.format(
                topic=state.topic,
                landscape_summary=sections["landscape"][:400],
                key_questions=json.dumps(plan.get("key_questions", []), ensure_ascii=False),
            ), "Issues & Opportunities", callback)
        sections["issues"] = s

        # Strategic Implications
        s = await self._write_section(
            _STRATEGY_IMPLICATIONS.format(
                topic=state.topic,
                findings=findings,
                issues_summary=sections["issues"][:400],
            ), "Strategic Implications", callback)
        sections["implications"] = s

        # Recommendations
        s = await self._write_section(
            _STRATEGY_RECOMMENDATIONS.format(
                topic=state.topic,
                implications_summary=sections["implications"][:400],
                review_feedback=review_fb,
            ), "Recommendations", callback)
        sections["recommendations"] = s

        # Conclusion
        s = await self._write_section(
            _STRATEGY_CONCLUSION.format(
                topic=state.topic,
                recommendations_summary=sections["recommendations"][:400],
                strategy=plan.get("strategy", "")[:200],
            ), "Conclusion", callback)
        sections["conclusion"] = self._enforce_conclusion(s)

        state.section_documents = sections

        date = datetime.now().strftime("%Y년 %m월 %d일")
        doc = f"# {state.topic} — AI 전략 분석 리포트\n\n"
        doc += f"> 작성일: {date} | Multi-Agent Research System\n\n"
        doc += sections["exec_summary"] + "\n\n---\n\n"
        doc += sections["background"] + "\n\n"
        doc += sections["landscape"] + "\n\n"
        doc += sections["issues"] + "\n\n"
        doc += sections["implications"] + "\n\n"
        doc += sections["recommendations"] + "\n\n"
        doc += sections["conclusion"] + "\n\n"

        if state.references:
            doc += f"## References (APA)\n\n"
            doc += "\n\n".join(state.references)

        return doc

    # ── 공개 진입점 ─────────────────────────────────────────────

    async def write(self, state: ResearchState,
                    section_callback: Optional[Callable] = None) -> str:
        self.print_status("섹션별 분할 문서 작성 시작...")
        if self.mode == "academic":
            return await self._write_academic(state, section_callback)
        else:
            return await self._write_strategy(state, section_callback)
