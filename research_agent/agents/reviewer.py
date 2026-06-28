# agents/reviewer.py
# Stage 5: Multi-persona 리뷰 (Methodology Hawk + Novelty Skeptic + Impact Evaluator)

import asyncio
import json
from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_ORCHESTRATOR

PERSONAS = {
    "methodology_hawk": {
        "system": "당신은 연구 방법론의 엄격한 비평가입니다. 방법론의 약점과 논리적 오류를 찾아내세요. JSON만 반환하세요.",
        "focus": "방법론의 엄밀성, 실험 설계의 타당성, 통계적 유의성"
    },
    "novelty_skeptic": {
        "system": "당신은 연구 참신성에 회의적인 평가자입니다. 기존 연구와의 차별성을 냉정하게 검토하세요. JSON만 반환하세요.",
        "focus": "기존 연구 대비 차별성, 참신성의 실질적 가치"
    },
    "impact_evaluator": {
        "system": "당신은 연구의 실용적 영향력을 평가하는 전문가입니다. 현실적 적용 가능성을 검토하세요. JSON만 반환하세요.",
        "focus": "실용성, 산업/학계 영향력, 확장 가능성"
    },
}

REVIEW_PROMPT = """
연구 주제: {topic}
선정 아이디어: {idea}
실험 설계: {experiment}
평가 관점: {focus}

다음 JSON 형식으로 평가하세요:
{{
  "score": 0.0~1.0,
  "strengths": ["강점1", "강점2"],
  "weaknesses": ["약점1", "약점2"],
  "feedback": "개선을 위한 구체적 피드백"
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
