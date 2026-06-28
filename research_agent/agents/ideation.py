# agents/ideation.py
# Stage 3: 아이디어 생성 → 참신성 평가 → 최적 선정

from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_ORCHESTRATOR

SYSTEM_GEN = """당신은 창의적인 AI 연구자입니다.
수집된 자료를 바탕으로 참신한 연구 아이디어를 제안하세요.
JSON만 반환하세요."""

SYSTEM_EVAL = """당신은 엄격한 연구 아이디어 평가자입니다.
각 아이디어의 참신성, 실현가능성, 임팩트를 평가하세요.
JSON만 반환하세요."""

GENERATE_PROMPT = """
주제: {topic}
모드: {mode}

수집된 핵심 발견:
{findings}

위 자료를 기반으로 연구 아이디어 3개를 제안하세요:
{{
  "ideas": [
    {{
      "title": "아이디어 제목",
      "hypothesis": "가설 또는 핵심 주장",
      "approach": "접근 방법",
      "novelty": "기존 연구 대비 차별점",
      "feasibility": "실현 가능성 (높음/중간/낮음)"
    }}
  ]
}}"""

REVISE_PROMPT = """
기존 아이디어:
{idea}

리뷰어 피드백:
{feedback}

피드백을 반영하여 개선된 아이디어를 JSON으로 반환하세요.
(같은 형식 유지)"""


class IdeationAgent(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("IdeationAgent", MODEL_ORCHESTRATOR, verbose)
        self.mode = mode

    def _format_findings(self, summaries: list) -> str:
        lines = []
        for s in summaries[:5]:
            sd = s.get("summary_data", {})
            findings = sd.get("key_findings", [])
            if findings:
                lines.append(f"- {sd.get('title','')}: {'; '.join(findings[:2])}")
        return "\n".join(lines) or "자료 없음"

    async def generate(self, state: ResearchState) -> list[dict]:
        self.print_status("아이디어 생성 중...")
        findings = self._format_findings(state.summaries)
        prompt = GENERATE_PROMPT.format(
            topic=state.topic, mode=state.mode, findings=findings
        )
        response = await self.call_llm(SYSTEM_GEN, prompt, temperature=0.85)
        data = self.parse_json(response)
        return data.get("ideas", [])

    async def select_best(self, ideas: list[dict], state: ResearchState) -> dict:
        self.print_status("최적 아이디어 선정 중...")
        if not ideas:
            return {}
        if len(ideas) == 1:
            return ideas[0]

        eval_prompt = f"""다음 아이디어들을 평가하고 최적을 선정하세요:
{self._format_ideas(ideas)}

JSON:
{{
  "best_index": 0,
  "reason": "선정 이유",
  "score": 0.85
}}"""
        response = await self.call_llm(SYSTEM_EVAL, eval_prompt, temperature=0.3)
        result = self.parse_json(response)
        idx = result.get("best_index", 0)
        return ideas[min(idx, len(ideas)-1)]

    async def revise(self, state: ResearchState, feedback: str) -> dict:
        self.print_status("아이디어 revision 중...")
        import json
        prompt = REVISE_PROMPT.format(
            idea=json.dumps(state.selected_idea, ensure_ascii=False),
            feedback=feedback
        )
        response = await self.call_llm(SYSTEM_GEN, prompt, temperature=0.7)
        revised = self.parse_json(response)
        return revised if revised else state.selected_idea

    def _format_ideas(self, ideas: list) -> str:
        lines = []
        for i, idea in enumerate(ideas):
            lines.append(f"[{i}] {idea.get('title','')}: {idea.get('novelty','')}")
        return "\n".join(lines)
