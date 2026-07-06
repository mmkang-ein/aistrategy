# agents/executor.py
# Stage 4: 실험 설계 + 코드 생성 (academic) / 검증 방법 설계 (strategy)

import json
from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_ORCHESTRATOR, MODEL_WORKER, MAX_TOKENS_WRITER, MAX_TOKENS_SECTION_RETRY_CAP

SYSTEM_DESIGN  = "당신은 연구 실험 설계 전문가입니다. JSON만 반환하세요."
SYSTEM_CODE    = "당신은 Python 연구 코드 전문가입니다. 실행 가능한 코드만 반환하세요 (주석 포함)."
SYSTEM_TABLES  = "You are a research data specialist. Return ONLY valid JSON with markdown table strings."

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

TABLE_PROMPT = """
Research topic: {topic}
Experiment design: {experiment_json}
Primary metrics: {metrics}

Generate 3 markdown comparison tables. Return ONLY this JSON structure:
{{
  "model_comparison": "| Model | {m1} | {m2} | Params | Notes |\\n|---|---|---|---|---|\\n| Baseline | ... | ... | ... | ... |\\n| Proposed | ... | ... | ... | ✓ Ours |\\n| SOTA-A | ... | ... | ... | ... |\\n| SOTA-B | ... | ... | ... | ... |",
  "experiment_env": "| Setting | Value |\\n|---|---|\\n| GPU | ... |\\n| Framework | ... |\\n| Epochs | ... |\\n| Batch Size | ... |\\n| Optimizer | ... |\\n| Learning Rate | ... |",
  "ablation": "| Component | Enabled | {m1} | Δ |\\n|---|---|---|---|\\n| Full Model | ✓ | ... | - |\\n| w/o Module A | ✗ | ... | ... |\\n| w/o Module B | ✗ | ... | ... |\\n| Baseline only | ✗ | ... | ... |"
}}

Use realistic values based on current research standards for this topic.
All table cell values must be filled with plausible numbers or text."""


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

    async def generate_tables(self, state: ResearchState) -> dict:
        self.print_status("실험 비교 테이블 생성 중...")
        metrics = state.experiment.get("metrics", ["Accuracy", "F1-Score"])
        m1 = metrics[0] if metrics else "Accuracy"
        m2 = metrics[1] if len(metrics) > 1 else "F1-Score"
        prompt = TABLE_PROMPT.format(
            topic=state.topic,
            experiment_json=json.dumps(state.experiment, ensure_ascii=False)[:600],
            metrics=", ".join(metrics[:4]),
            m1=m1,
            m2=m2,
        )
        # worker 모델로 빠르게 생성
        agent = type(self)(self.mode, self.verbose)
        agent.model = MODEL_WORKER
        response = await agent.call_llm(SYSTEM_TABLES, prompt, max_tokens=2000, temperature=0.3)
        tables = self.parse_json(response)
        if not isinstance(tables, dict):
            tables = {}
        self.logger.info(f"Tables generated: {list(tables.keys())}")
        return tables

    async def generate_code(self, state: ResearchState) -> str:
        self.print_status("분석 코드 생성 중...")
        prompt = CODE_PROMPT.format(
            topic=state.topic,
            experiment=json.dumps(state.experiment, ensure_ascii=False)
        )
        # 시뮬레이션/분석 코드는 수백 줄이 되는 경우가 많아 기본 토큰 상한(4096)으로는
        # 자주 잘림 — 명시적으로 넉넉한 상한을 주고, 그래도 잘리면 한 번 더 시도한다.
        code, stop_reason = await self.call_llm(
            SYSTEM_CODE, prompt, temperature=0.3,
            max_tokens=MAX_TOKENS_WRITER, label="code_snippet", return_meta=True,
        )
        if stop_reason == "max_tokens":
            retry_tokens = MAX_TOKENS_SECTION_RETRY_CAP + MAX_TOKENS_WRITER
            self.logger.warning(
                f"코드 생성이 max_tokens={MAX_TOKENS_WRITER}에서 잘림 — "
                f"max_tokens={retry_tokens}로 1회 재시도"
            )
            code, stop_reason = await self.call_llm(
                SYSTEM_CODE, prompt, temperature=0.3,
                max_tokens=retry_tokens, label="code_snippet (retry)", return_meta=True,
            )
            if stop_reason == "max_tokens":
                self.logger.warning("코드 생성이 재시도에도 잘림 — 그대로 사용 (수동 확인 필요)")
        # 마크다운 펜스 제거
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
        return code
