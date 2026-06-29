# agents/manager.py
# Stage 1: 주제 파싱 & 연구 전략 수립

from core.base_agent import BaseAgent
from config.settings import MODEL_ORCHESTRATOR

SYSTEM_ACADEMIC = """당신은 컴퓨터비전·AI 분야 시니어 연구자입니다 (NeurIPS·ICML·CVPR 논문 다수 게재 경험).
주어진 연구 주제를 분석하고 체계적인 연구 전략을 JSON으로 반환하세요.
반드시 JSON만 반환하고 다른 텍스트는 포함하지 마세요."""

SYSTEM_STRATEGY = """당신은 McKinsey·Gartner급 AI 전략 분석 전문가입니다.
주어진 주제를 분석하고 전략 리포트 작성을 위한 계획을 JSON으로 반환하세요.
반드시 JSON만 반환하고 다른 텍스트는 포함하지 마세요."""

PLAN_PROMPT_ACADEMIC = """
연구 주제: {topic}
현재 연도: 2026년

다음 JSON 형식으로 학술 연구 계획을 수립하세요.
search_queries는 정확히 10개를 생성하되, 아래 유형을 반드시 포함하세요:
- arxiv 최신 논문용 (예: "site:arxiv.org 2024 2025 {핵심기술}")
- survey/review 논문용 (예: "survey review {주제} deep learning 2024")
- 벤치마크·SOTA 비교용 (예: "state-of-the-art benchmark {주제} 2025")
- 핵심 방법론·알고리즘명 직접 검색
- 경쟁 기술·대안 접근법 비교
- 실용 구현·오픈소스 검색

{{
  "strategy": "연구 전략 요약 (3-4문장, 핵심 접근법과 차별화 포인트 포함)",
  "key_questions": ["핵심 연구 질문 1", "핵심 연구 질문 2", "핵심 연구 질문 3", "핵심 연구 질문 4"],
  "search_queries": [
    "arxiv 최신 논문 검색어 (영문, 2024-2025 포함)",
    "survey/review 논문 검색어 (영문)",
    "SOTA·벤치마크 비교 검색어 (영문)",
    "핵심 방법론명 직접 검색어 (영문)",
    "경쟁 기술·대안 비교 검색어 (영문)",
    "오픈소스·구현 관련 검색어 (영문, GitHub 포함)",
    "응용 분야 특화 검색어 (영문)",
    "한국 연구 현황 검색어 (한글)",
    "산업 적용 사례 검색어 (영문)",
    "한계점·미해결 문제 검색어 (영문, limitations challenges 포함)"
  ],
  "expected_contributions": ["학술적 기여점1 (구체적)", "기여점2 (구체적)", "기여점3"],
  "scope": "연구 범위, 전제 조건, 주요 제한사항"
}}
"""

PLAN_PROMPT_STRATEGY = """
분석 주제: {topic}
현재 연도: 2026년

다음 JSON 형식으로 전략 분석 계획을 수립하세요.
search_queries는 정확히 10개를 생성하되, 아래 유형을 반드시 포함하세요:
- 글로벌 트렌드·시장 현황 (McKinsey, Gartner, BCG 리포트 등)
- 주요 플레이어·경쟁 구도 분석
- 규제·정책 동향 (정부·기관 공식 발표)
- 기술 성숙도·ROI 분석
- 성공·실패 사례 연구 (case study)
- 한국 시장·정책 특화 정보

{{
  "strategy": "분석 전략 요약 (3-4문장, 핵심 관점과 접근법 포함)",
  "key_questions": ["전략적 핵심 질문 1", "핵심 질문 2", "핵심 질문 3", "핵심 질문 4"],
  "search_queries": [
    "글로벌 시장 현황·규모 검색어 (영문, 2024-2026 포함)",
    "McKinsey/Gartner/BCG 리포트 검색어 (영문)",
    "주요 기업·플레이어 전략 검색어 (영문)",
    "규제·정책·거버넌스 검색어 (영문)",
    "기술 ROI·도입 효과 분석 검색어 (영문)",
    "성공 사례 검색어 (영문, case study 포함)",
    "실패·리스크 사례 검색어 (영문, challenges failures 포함)",
    "한국 정책·시장 동향 검색어 (한글)",
    "스타트업·투자 트렌드 검색어 (영문)",
    "미래 전망·예측 검색어 (영문, forecast outlook 2025 2026 포함)"
  ],
  "expected_contributions": ["전략적 인사이트1 (구체적)", "인사이트2 (구체적)", "인사이트3"],
  "scope": "분석 범위, 지역·시장 범위, 주요 전제 조건"
}}
"""


class ManagerAgent(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("ManagerAgent", MODEL_ORCHESTRATOR, verbose)
        self.mode = mode
        self.system = SYSTEM_ACADEMIC if mode == "academic" else SYSTEM_STRATEGY

    async def plan(self, topic: str) -> dict:
        self.print_status(f"연구 계획 수립 중: {topic[:50]}")
        prompt_template = PLAN_PROMPT_ACADEMIC if self.mode == "academic" else PLAN_PROMPT_STRATEGY
        prompt = prompt_template.format(topic=topic)
        response = await self.call_llm(self.system, prompt, temperature=0.5)
        plan = self.parse_json(response)
        self.logger.info(f"Plan 완료 | queries={len(plan.get('search_queries', []))}")
        return plan
