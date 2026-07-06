# core/base_agent.py
# 모든 에이전트가 상속받는 베이스 클래스

import json
import anthropic
from config.settings import (
    ANTHROPIC_API_KEY, MODEL_ORCHESTRATOR, MODEL_WORKER, MAX_TOKENS_DEFAULT
)
from core.logger import get_logger


class BaseAgent:
    """
    공통 기능:
    - Anthropic API 호출 (call_llm)
    - JSON 파싱 헬퍼
    - 로깅
    """

    def __init__(self, name: str, model: str = None, verbose: bool = False):
        self.name    = name
        self.model   = model or MODEL_ORCHESTRATOR
        self.verbose = verbose
        self.logger  = get_logger(name)
        self.client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    async def call_llm(
        self,
        system: str,
        user:   str,
        max_tokens: int = MAX_TOKENS_DEFAULT,
        temperature: float = 0.7,
        label: str = None,
        return_meta: bool = False,
    ):
        """Claude API 호출 → 텍스트 반환.
        return_meta=True면 (text, stop_reason) 튜플을 반환한다.
        stop_reason == 'max_tokens'면 응답이 중간에 잘렸다는 뜻이므로,
        verbose 여부와 무관하게 항상 경고 로그를 남긴다 (내용 손실을 조용히 넘기지 않기 위함)."""
        if self.verbose:
            self.logger.debug(f"[{self.name}] 호출 | model={self.model} | prompt[:80]={user[:80]}")

        # 동기 SDK를 asyncio로 감싸기
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=temperature,
            )
        )
        text = response.content[0].text
        stop_reason = getattr(response, "stop_reason", None)
        tag = f" ({label})" if label else ""
        if stop_reason == "max_tokens":
            self.logger.warning(
                f"[{self.name}]{tag} 응답이 max_tokens={max_tokens}에서 잘림 "
                f"(stop_reason=max_tokens) — 내용이 중간에 끊겼을 수 있음"
            )
        if self.verbose:
            self.logger.debug(f"[{self.name}]{tag} 응답 길이: {len(text)}자 | stop_reason={stop_reason}")
        if return_meta:
            return text, stop_reason
        return text

    def parse_json(self, text: str) -> dict | list:
        """LLM 응답에서 JSON 추출 (마크다운 펜스 포함 처리)"""
        text = text.strip()
        # ```json ... ``` 제거
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON 파싱 실패: {e} | 원문: {text[:200]}")
            return {}

    def print_status(self, msg: str):
        print(f"  [{self.name}] {msg}")
