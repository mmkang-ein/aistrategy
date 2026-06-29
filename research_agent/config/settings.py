# config/settings.py
# 시스템 전체 설정 — 여기서 모델, API, 경로 등을 관리

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# ─── Anthropic API ────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 에이전트별 모델 분리 (비용·품질 균형)
MODEL_ORCHESTRATOR = "claude-sonnet-4-6"   # Manager, Writer, Review
MODEL_WORKER       = "claude-haiku-4-5-20251001"  # Lit Agent, Summarizer (병렬·대량)

MAX_TOKENS_DEFAULT = 4096
MAX_TOKENS_WRITER  = 8192


# ─── 검색 설정 ────────────────────────────────────────────────
@dataclass
class SearchConfig:
    max_results_per_query: int = 5
    max_parallel_queries:  int = 10      # Lit Agent 병렬 수
    search_timeout_sec:    int = 30
    sources_academic: list = field(default_factory=lambda: [
        "arxiv.org", "scholar.google.com", "semanticscholar.org",
        "ieee.org", "acm.org"
    ])
    sources_strategy: list = field(default_factory=lambda: [
        "mckinsey.com", "gartner.com", "mit.edu", "stanford.edu",
        "oecd.org", "brookings.edu"
    ])


# ─── 파이프라인 설정 ──────────────────────────────────────────
@dataclass
class PipelineConfig:
    max_papers:    int = 10
    max_revisions: int = 2
    review_threshold: float = 0.7    # 이 점수 미만이면 revision
    enable_coder_agent: bool = True  # academic 모드에서 실험 코드 생성


# ─── 출력 경로 ────────────────────────────────────────────────
OUTPUT_DIRS = {
    "academic": BASE_DIR / "outputs" / "papers",
    "strategy": BASE_DIR / "outputs" / "reports",
}
LOG_DIR  = BASE_DIR / "logs"
PROMPT_DIR = BASE_DIR / "prompts"

# 디렉토리 자동 생성
for d in [*OUTPUT_DIRS.values(), LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ─── 단계별 레이블 (로그·UI용) ────────────────────────────────
STAGE_LABELS = {
    1: "① Input      — 주제 파싱 & 전략 수립",
    2: "② Literature — 자료 수집 & 요약",
    3: "③ Ideation   — 아이디어 생성 & 평가",
    4: "④ Execution  — 실험 설계 & 코드",
    5: "⑤ Review     — 다각도 비판 검토",
    6: "⑥ Output     — 최종 문서 작성",
}
