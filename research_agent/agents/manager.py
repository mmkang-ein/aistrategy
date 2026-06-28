# agents/manager.py
# Stage 1: 주제 파싱 & 연구 전략 수립

from core.base_agent import BaseAgent
from config.settings import MODEL_ORCHESTRATOR

SYSTEM_ACADEMIC = """당신은 컴퓨터비전·AI 분야 시니어 연구자입니다.
주어진 연구 주제를 분석하고 체계적인 연구 전략을 JSON으로 반환하세요.
반드시 JSON만 반환하고 다른 텍스트는 포함하지 마세요."""

SYSTEM_STRATEGY = """당신은 AI 전략 분석 전문가입니다.
주어진 주제를 분석하고 전략 리포트 작성을 위한 계획을 JSON으로 반환하세요.
반드시 JSON만 반환하고 다른 텍스트는 포함하지 마세요."""

PLAN_PROMPT = """
주제: {topic}
모드: {mode}

다음 JSON 형식으로 연구 계획을 수립하세요:
{{
  "strategy": "연구 전략 요약 (2-3문장)",
  "key_questions": ["핵심 질문 1", "핵심 질문 2", "핵심 질문 3"],
  "search_queries": ["검색어1 (영문)", "검색어2", "검색어3", "검색어4", "검색어5"],
  "expected_contributions": ["기여점1", "기여점2"],
  "scope": "연구 범위 및 제한사항"
}}
"""


class ManagerAgent(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("ManagerAgent", MODEL_ORCHESTRATOR, verbose)
        self.mode = mode
        self.system = SYSTEM_ACADEMIC if mode == "academic" else SYSTEM_STRATEGY

    async def plan(self, topic: str) -> dict:
        self.print_status(f"연구 계획 수립 중: {topic[:50]}")
        prompt = PLAN_PROMPT.format(topic=topic, mode=self.mode)
        response = await self.call_llm(self.system, prompt, temperature=0.5)
        plan = self.parse_json(response)
        self.logger.info(f"Plan 완료 | queries={len(plan.get('search_queries', []))}")
        return plan
