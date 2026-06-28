# agents/executor.py
# Stage 4: 실험 설계 + 코드 생성 (academic) / 검증 방법 설계 (strategy)

import json
from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_ORCHESTRATOR

SYSTEM_DESIGN = "당신은 연구 실험 설계 전문가입니다. JSON만 반환하세요."
SYSTEM_CODE   = "당신은 Python 연구 코드 전문가입니다. 실행 가능한 코드만 반환하세요 (주석 포함)."

DESIGN_PROMPT = """
선정 아이디어: {idea}
연구 모드: {mode}

실험/검증 계획을 JSON으로 작성하세요:
{{
  "method": "방법론 요약",
  "steps": ["단계1", "단계2", "단계3"],
  "metrics": ["평가지표1", "평가지표2"],
  "datasets": ["데이터셋/자료"],
  "expected_results": "예상 결과"
}}"""

CODE_PROMPT = """
연구 주제: {topic}
실험 계획: {experiment}

이 실험을 위한 Python 분석 코드를 작성하세요.
- 필요한 라이브러리 import
- 데이터 로드/전처리 템플릿
- 핵심 분석 함수
- 결과 시각화 (matplotlib)
주석을 한국어로 작성하세요."""


class ExecutorAgent(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("ExecutorAgent", MODEL_ORCHESTRATOR, verbose)
        self.mode = mode

    async def design(self, state: ResearchState) -> dict:
        self.print_status("실험/검증 방법 설계 중...")
        prompt = DESIGN_PROMPT.format(
            idea=json.dumps(state.selected_idea, ensure_ascii=False),
            mode=state.mode
        )
        response = await self.call_llm(SYSTEM_DESIGN, prompt, temperature=0.4)
        return self.parse_json(response)

    async def generate_code(self, state: ResearchState) -> str:
        self.print_status("분석 코드 생성 중...")
        prompt = CODE_PROMPT.format(
            topic=state.topic,
            experiment=json.dumps(state.experiment, ensure_ascii=False)
        )
        code = await self.call_llm(SYSTEM_CODE, prompt, temperature=0.3)
        # 마크다운 펜스 제거
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
        return code
