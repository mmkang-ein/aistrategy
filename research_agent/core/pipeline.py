# core/pipeline.py
# 6-stage 파이프라인 오케스트레이터

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import (
    OUTPUT_DIRS, STAGE_LABELS, PipelineConfig, SearchConfig
)
from core.logger import get_logger
from core.state import ResearchState

from agents.manager    import ManagerAgent
from agents.searcher   import SearcherAgent
from agents.summarizer import SummarizerAgent
from agents.ideation   import IdeationAgent
from agents.executor   import ExecutorAgent
from agents.reviewer   import ReviewerAgent
from agents.writer     import WriterAgent

logger = get_logger(__name__)


class ResearchPipeline:
    def __init__(
        self,
        mode: str,
        topic: str,
        max_papers: int = 10,
        max_revisions: int = 2,
        output_dir: Optional[str] = None,
        verbose: bool = False,
    ):
        self.mode  = mode
        self.topic = topic
        self.cfg   = PipelineConfig(max_papers=max_papers, max_revisions=max_revisions)
        self.search_cfg = SearchConfig()
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIRS[mode]
        self.verbose = verbose

        # 공유 상태 객체 (에이전트 간 데이터 전달)
        self.state = ResearchState(mode=mode, topic=topic)

        # 에이전트 초기화
        self.manager    = ManagerAgent(mode, verbose)
        self.searcher   = SearcherAgent(mode, self.search_cfg, verbose)
        self.summarizer = SummarizerAgent(mode, verbose)
        self.ideation   = IdeationAgent(mode, verbose)
        self.executor   = ExecutorAgent(mode, verbose)
        self.reviewer   = ReviewerAgent(mode, verbose)
        self.writer     = WriterAgent(mode, verbose)

    def _print_stage(self, stage_num: int):
        label = STAGE_LABELS.get(stage_num, f"Stage {stage_num}")
        print(f"\n{'─'*60}")
        print(f"  {label}")
        print(f"{'─'*60}")

    async def run(self) -> dict:
        logger.info(f"Pipeline 시작 | mode={self.mode} | topic={self.topic}")
        self.state.started_at = datetime.now()

        # ── Stage 1: Input ────────────────────────────────────
        self._print_stage(1)
        plan = await self.manager.plan(self.topic)
        self.state.plan = plan
        print(f"  전략: {plan.get('strategy', '')[:80]}...")

        # ── Stage 2: Literature / Trend 수집 ──────────────────
        self._print_stage(2)
        queries = plan.get("search_queries", [self.topic])
        raw_results = await self.searcher.search_parallel(queries, self.cfg.max_papers)
        self.state.raw_sources = raw_results
        print(f"  수집 완료: {len(raw_results)}건")

        summaries = await self.summarizer.summarize_all(raw_results)
        self.state.summaries = summaries
        print(f"  요약 완료: {len(summaries)}건")

        # ── Stage 3: Ideation / Analysis ──────────────────────
        self._print_stage(3)
        ideas = await self.ideation.generate(self.state)
        self.state.ideas = ideas
        print(f"  아이디어 {len(ideas)}개 생성")

        best_idea = await self.ideation.select_best(ideas, self.state)
        self.state.selected_idea = best_idea
        print(f"  선정: {best_idea.get('title', '')}")

        # ── Stage 4: Execution ────────────────────────────────
        self._print_stage(4)
        experiment = await self.executor.design(self.state)
        self.state.experiment = experiment

        if self.mode == "academic" and self.cfg.enable_coder_agent:
            code = await self.executor.generate_code(self.state)
            self.state.code_snippet = code
            print(f"  실험 설계 + 코드 생성 완료")
        else:
            print(f"  실험/검증 설계 완료")

        # ── Stage 5: Review (revision loop) ───────────────────
        self._print_stage(5)
        revision_count = 0
        while revision_count <= self.cfg.max_revisions:
            review = await self.reviewer.review(self.state)
            self.state.reviews.append(review)
            score = review.get("score", 1.0)
            print(f"  리뷰 #{revision_count+1} — 점수: {score:.2f}")

            if score >= self.cfg.review_threshold:
                print(f"  ✓ 품질 기준 통과")
                break
            if revision_count >= self.cfg.max_revisions:
                print(f"  ⚠ 최대 revision 도달, 진행")
                break

            # revision: Stage 3으로 피드백
            print(f"  → revision #{revision_count+1} 시작...")
            feedback = review.get("feedback", "")
            best_idea = await self.ideation.revise(self.state, feedback)
            self.state.selected_idea = best_idea
            experiment = await self.executor.design(self.state)
            self.state.experiment = experiment
            revision_count += 1

        # ── Stage 6: Output ───────────────────────────────────
        self._print_stage(6)
        document = await self.writer.write(self.state)
        self.state.final_document = document

        output_path = self._save_output(document)
        self.state.output_path = str(output_path)
        self.state.finished_at = datetime.now()

        self._save_state_log()
        return {"output_path": str(output_path), "state": self.state.to_dict()}

    def _save_output(self, document: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = self.topic[:40].replace(" ", "_").replace("/", "-")
        filename = f"{self.mode}_{safe_topic}_{timestamp}.md"
        path = self.output_dir / filename
        path.write_text(document, encoding="utf-8")
        logger.info(f"Output saved: {path}")
        return path

    def _save_state_log(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = Path("logs") / f"state_{timestamp}.json"
        log_path.write_text(
            json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
