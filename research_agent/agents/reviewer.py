# agents/reviewer.py
# Stage 5: Multi-persona 리뷰 (Methodology Hawk + Novelty Skeptic + Impact Evaluator)

import asyncio
import json
from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_ORCHESTRATOR

PERSONAS = {
    "methodology_hawk": {
        "system": """당신은 NeurIPS·ICML급 연구 방법론 심사자입니다.
아이디어 단계의 연구를 현실적으로 평가하세요. 완성된 논문이 아닌 연구 제안임을 감안합니다.

점수 기준 (반드시 이 기준을 따르세요):
- 0.85~1.0: 방법론이 탁월하고 선도적, 설계 완전성 높음
- 0.75~0.85: 방법론 타당, 핵심 설계 건전, 소규모 보완 필요
- 0.65~0.75: 방법론 합리적, 일부 실험 설계 보완 필요 (기본 아이디어는 valid)
- 0.55~0.65: 방법론 약점 존재, 명확한 수정 필요
- 0.55미만: 방법론 근본 문제

합리적인 연구 아이디어라면 0.65 이상을 기본으로 평가하세요. JSON만 반환하세요.""",
        "focus": "방법론 엄밀성(실험 설계·통계 타당성·재현성·비교 기준선), 단 아이디어 단계임을 감안"
    },
    "novelty_skeptic": {
        "system": """당신은 연구 참신성 전문 평가자입니다. 냉정하되 공정하게 차별성을 검토하세요.
기존 연구와 비교해 의미 있는 기여가 있는지 판단합니다.

점수 기준 (반드시 이 기준을 따르세요):
- 0.85~1.0: 획기적 참신성, 분야 패러다임 전환 가능
- 0.75~0.85: 명확한 차별성, 기존 연구의 중요한 gap 해소
- 0.65~0.75: 의미 있는 기여, 기존 연구 개선·확장 (충분히 가치 있음)
- 0.55~0.65: 점진적 개선, 차별성 보완 필요
- 0.55미만: 기존 연구 반복 수준

기존 연구를 명확히 개선하는 아이디어라면 0.65 이상으로 평가하세요. JSON만 반환하세요.""",
        "focus": "기존 연구 대비 차별성, 참신성의 실질적 학술·산업 가치, 연구 gap 해소 여부"
    },
    "impact_evaluator": {
        "system": """당신은 연구 영향력 및 실용성 평가 전문가입니다.
단기·중기·장기 관점에서 현실적 파급력을 평가하세요.

점수 기준 (반드시 이 기준을 따르세요):
- 0.85~1.0: 산업·학계에 즉각적·광범위한 영향, 높은 확장성
- 0.75~0.85: 명확한 실용 가치, 구체적 적용 분야 다수
- 0.65~0.75: 의미 있는 영향력, 특정 도메인 기여 확실 (충분히 가치 있음)
- 0.55~0.65: 제한적 영향, 적용 범위 협소
- 0.55미만: 실용적 가치 불명확

명확한 적용 분야가 있는 연구라면 0.65 이상으로 평가하세요. JSON만 반환하세요.""",
        "focus": "실용성·확장성, 산업/학계 영향력, ROI 및 구현 가능성, 단기·중기 파급 효과"
    },
}

REVIEW_PROMPT = """
연구 주제: {topic}
선정 아이디어: {idea}
실험 설계: {experiment}
평가 관점: {focus}

[중요] 이것은 완성 논문이 아닌 연구 아이디어·제안 단계입니다.
합리적인 연구 방향이라면 최소 0.65 이상을 기준으로 평가하세요.
강점을 충분히 인정하고, 약점은 개선 방향 중심으로 서술하세요.

다음 JSON 형식으로 평가하세요:
{{
  "score": 0.0~1.0,
  "strengths": ["구체적 강점1", "구체적 강점2", "구체적 강점3"],
  "weaknesses": ["약점1 (개선 방향 포함)", "약점2 (개선 방향 포함)"],
  "feedback": "점수 근거와 핵심 개선점을 3-4문장으로 서술. 가장 중요한 개선 액션 포함."
}}"""


class ReviewerAgent(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("ReviewerAgent", MODEL_ORCHESTRATOR, verbose)

    async def _review_one(self, persona_name: str, persona: dict, state: ResearchState) -> dict:
        self.print_status(f"{persona_name} 리뷰 중...")
        prompt = REVIEW_PROMPT.format(
            topic=state.topic,
            idea=json.dumps(state.selected_idea, ensure_ascii=False),
            experiment=json.dumps(state.experiment, ensure_ascii=False),
            focus=persona["focus"]
        )
        response = await self.call_llm(persona["system"], prompt, temperature=0.4)
        result = self.parse_json(response)
        return {"persona": persona_name, **result}

    async def review(self, state: ResearchState) -> dict:
        """3개 페르소나 병렬 리뷰 → 앙상블 점수"""
        tasks = [
            self._review_one(name, persona, state)
            for name, persona in PERSONAS.items()
        ]
        reviews = await asyncio.gather(*tasks)

        scores = [r.get("score", 0.5) for r in reviews]
        avg_score = sum(scores) / len(scores)

        # 약점·피드백 통합
        all_weaknesses = []
        all_feedback = []
        for r in reviews:
            all_weaknesses.extend(r.get("weaknesses", []))
            if r.get("feedback"):
                all_feedback.append(f"[{r['persona']}] {r['feedback']}")

        self.print_status(f"앙상블 점수: {avg_score:.2f} (개별: {[f'{s:.2f}' for s in scores]})")

        return {
            "score":      avg_score,
            "individual": reviews,
            "weaknesses": list(set(all_weaknesses)),
            "feedback":   "\n".join(all_feedback),
        }
