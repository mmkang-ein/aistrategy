# tools/paper_enhancer.py
# 기존 .md 논문/리포트 분석 → 그림·테이블 자동 추가 (FigureBuilder + export.py 활용)

import re
from pathlib import Path
from typing import Callable, Optional

from core.base_agent import BaseAgent
from core.state import ResearchState
from agents.figure_builder import FigureBuilder
from config.settings import MODEL_WORKER, BASE_DIR

FIG_DIR = BASE_DIR / "outputs" / "figures"

TABLE_SYSTEM = "You are a research data specialist. Return ONLY valid JSON with markdown table strings."

TABLE_PROMPT = """
Paper title: {title}
Paper mode: {mode}
Paper content (excerpt):
{excerpt}

Generate 3 markdown comparison tables consistent with this paper's methodology, claims, and results.
Return ONLY this JSON structure:
{{
  "model_comparison": "| Model | {m1} | Params | Notes |\\n|---|---|---|---|\\n| Baseline | ... | ... | ... |\\n| Proposed | ... | ... | ✓ Ours |\\n| SOTA-A | ... | ... | ... |\\n| SOTA-B | ... | ... | ... |",
  "experiment_env": "| Setting | Value |\\n|---|---|\\n| Framework | ... |\\n| Hardware | ... |\\n| Epochs / Iterations | ... |\\n| Key Hyperparameters | ... |",
  "ablation": "| Component | Enabled | {m1} | Δ |\\n|---|---|---|---|\\n| Full Model | ✓ | ... | - |\\n| w/o Module A | ✗ | ... | ... |\\n| w/o Module B | ✗ | ... | ... |"
}}

Use realistic values consistent with the paper's stated claims. All cells must be filled with plausible numbers or text."""


class TableGenerator(BaseAgent):
    """기존 논문 본문을 근거로 비교/환경/Ablation 테이블 생성"""

    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("TableGenerator", MODEL_WORKER, verbose)
        self.mode = mode

    async def generate(self, title: str, content: str, metric: str) -> dict:
        prompt = TABLE_PROMPT.format(
            title=title, mode=self.mode, excerpt=content[:3000], m1=metric,
        )
        response = await self.call_llm(TABLE_SYSTEM, prompt, max_tokens=2000, temperature=0.3)
        tables = self.parse_json(response)
        return tables if isinstance(tables, dict) else {}


# ── 마크다운 분석 헬퍼 ──────────────────────────────────────────

def _extract_title(md_text: str) -> str:
    for line in md_text.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return "Untitled"


def _extract_metric(md_text: str) -> str:
    m = re.search(r"\b(Accuracy|F1[- ]Score|BLEU|FCT|Latency|Throughput|mAP|AUC|Precision|Recall)\b",
                  md_text, re.I)
    return m.group(1) if m else "Score"


def _has_section(md_text: str, keyword: str) -> bool:
    return bool(re.search(rf"^##+\s.*{re.escape(keyword)}", md_text, re.I | re.M))


def _extract_steps(md_text: str) -> list:
    """'Method'/'방법' 관련 ## 섹션의 ### 하위 헤딩을 아키텍처 다이어그램 단계로 사용"""
    steps = []
    in_method = False
    for line in md_text.split("\n"):
        if re.match(r"^##\s", line):
            in_method = bool(re.search(r"method|방법", line, re.I))
            continue
        if in_method and re.match(r"^###\s", line):
            steps.append(re.sub(r"^###\s*[\d.]*\s*", "", line).strip())
    return steps[:6]


def _insert_before_references(md_text: str, insertion: str) -> str:
    m = re.search(r"^##\s+(references|참고문헌)", md_text, re.I | re.M)
    if m:
        idx = m.start()
        return md_text[:idx] + insertion + "\n\n" + md_text[idx:]
    return md_text.rstrip() + "\n\n" + insertion


def _tables_to_markdown(tables: dict) -> str:
    labels = {
        "model_comparison": "### Table 1: Model Comparison",
        "experiment_env":   "### Table 2: Experimental Environment",
        "ablation":         "### Table 3: Ablation Study",
    }
    body = "".join(
        f"{label}\n\n{tables[key]}\n\n"
        for key, label in labels.items() if tables.get(key)
    )
    return f"## Experimental Results\n\n{body}" if body else ""


def _figures_to_markdown(figures: list) -> str:
    body = ""
    for fig in figures:
        body += f"### {fig['title']}\n\n_{fig['caption']}_\n\n"
        if fig.get("path"):
            body += f"[Saved: `{fig['path']}`]\n\n"
    return f"## Figures\n\n{body}" if body else ""


# ── 메인 클래스 ─────────────────────────────────────────────────

class PaperEnhancer:
    """기존 .md 파일을 분석해 그림(아키텍처/성능/Ablation)과 비교 테이블을 자동 추가한다."""

    def __init__(self, mode: str, verbose: bool = False):
        self.mode = mode
        self.figure_builder  = FigureBuilder(mode, verbose)
        self.table_generator = TableGenerator(mode, verbose)

    async def enhance(self, md_path: Path, progress_cb: Optional[Callable[[str], None]] = None) -> dict:
        def report(msg: str):
            if progress_cb:
                progress_cb(msg)

        FIG_DIR.mkdir(parents=True, exist_ok=True)
        md_text = md_path.read_text(encoding="utf-8")
        title   = _extract_title(md_text)
        metric  = _extract_metric(md_text)

        has_figures_section = _has_section(md_text, "Figures")
        has_results_section = _has_section(md_text, "Experimental Results")

        state = ResearchState(mode=self.mode, topic=title)
        state.experiment = {"steps": _extract_steps(md_text), "metrics": [metric]}
        state.selected_idea = {"methodology": ""}

        figures: list = []
        prefix = re.sub(r"[^a-zA-Z0-9_-]", "_", md_path.stem)[:40]

        # ── 1단계: 그림 생성 중 (아키텍처 다이어그램) ──────────────
        report("그림 생성 중...")
        if not has_figures_section:
            png = self.figure_builder._architecture_diagram(state)
            if png:
                path = FIG_DIR / f"{prefix}_figure_1_architecture.png"
                self.figure_builder._save_png(png, path)
                figures.append({
                    "title":     "Figure 1: System Architecture",
                    "caption":   "Overview of the proposed system architecture with key components and data flow.",
                    "png_bytes": png,
                    "path":      str(path),
                })

        # ── 2단계: 테이블 변환 중 (LLM 테이블 생성 → 차트 변환) ────
        report("테이블 변환 중...")
        tables: dict = {}
        if not has_results_section:
            tables = await self.table_generator.generate(title, md_text, metric)
        state.experiment_tables = tables

        if not has_figures_section:
            if tables.get("model_comparison"):
                png = self.figure_builder._bar_chart(tables["model_comparison"], metric, title)
                if png:
                    path = FIG_DIR / f"{prefix}_figure_2_performance.png"
                    self.figure_builder._save_png(png, path)
                    figures.append({
                        "title":     "Figure 2: Performance Comparison",
                        "caption":   f"Comparison of proposed method vs. baselines on {metric}.",
                        "png_bytes": png,
                        "path":      str(path),
                    })
            if tables.get("ablation"):
                png = self.figure_builder._ablation_chart(tables["ablation"], metric, title)
                if png:
                    path = FIG_DIR / f"{prefix}_figure_3_ablation.png"
                    self.figure_builder._save_png(png, path)
                    figures.append({
                        "title":     "Figure 3: Ablation Study",
                        "caption":   "Impact of each proposed component on overall model performance.",
                        "png_bytes": png,
                        "path":      str(path),
                    })

        # ── 3단계: 완료 (문서 병합 & 저장) ─────────────────────────
        report("문서 병합 중...")
        new_md = md_text
        if tables and not has_results_section:
            new_md = _insert_before_references(new_md, _tables_to_markdown(tables))
        if figures and not has_figures_section:
            new_md = _insert_before_references(new_md, _figures_to_markdown(figures))

        if new_md != md_text:
            md_path.write_text(new_md, encoding="utf-8")

        report("완료")
        return {"md_text": new_md, "figures": figures, "tables": tables, "path": str(md_path)}
