# tools/paper_enhancer.py
# 기존 .md 논문/리포트 분석 → 그림·테이블 자동 추가 (FigureBuilder + export.py 활용)

import re
from pathlib import Path
from typing import Callable, Optional

from core.base_agent import BaseAgent
from core.state import ResearchState
from core.logger import get_logger
from agents.figure_builder import FigureBuilder
from agents.writer import SYSTEM_ACADEMIC
from config.settings import MODEL_WORKER, BASE_DIR, MAX_TOKENS_SECTION, MAX_TOKENS_SECTION_RETRY_CAP

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


# ── 섹션 완성도 검토·보완 (빠진 섹션 생성 + 부실한 섹션 재작성) ──────

# 논문 표준 섹션의 canonical 순서 (없는 섹션을 어디에 끼워 넣을지 판단하는 기준)
CANONICAL_ORDER = [
    "abstract", "introduction", "related_work", "methodology",
    "experiments", "discussion", "conclusion",
]

SECTION_LABELS = {
    "abstract":      "Abstract",
    "introduction":  "Introduction",
    "related_work":  "Related Work",
    "methodology":   "Methodology",
    "experiments":   "Experiments",
    "discussion":    "Discussion",
    "conclusion":    "Conclusion",
}

# 헤딩 텍스트에서 각 canonical 섹션을 식별하기 위한 키워드 (대소문자 무시)
SECTION_KEYWORDS = {
    "abstract":     [r"abstract"],
    "introduction": [r"introduction"],
    "related_work": [r"related\s*work", r"literature\s*review"],
    "methodology":  [r"method"],
    "experiments":  [r"experiment", r"evaluation", r"result"],
    "discussion":   [r"discussion"],
    "conclusion":   [r"conclusion"],
}

# 이 길이(문자 수) 미만이면 "부실한 섹션"으로 간주하고 재작성 대상이 됨
MIN_SECTION_LENGTH = {
    "abstract": 300, "introduction": 500, "related_work": 500,
    "methodology": 500, "experiments": 400, "discussion": 300, "conclusion": 200,
}

ENHANCE_SECTION_SYSTEM = SYSTEM_ACADEMIC

ENHANCE_SECTION_PROMPT = """다음은 기존 논문의 일부입니다.

논문 제목: {title}

논문 Abstract (참고용):
{abstract_excerpt}

{existing_note}
{existing_content}

## "{section_label}" 섹션을 작성하세요.
- 논문 전체의 주제, 방법론, 실험 설정과 일관되게 작성하세요.
- 이미 논문에 있는 내용(방법론, 실험 설정, 결과)을 근거로 논리적으로 확장하세요 — 없는
  사실이나 수치를 새로 지어내지 마세요.
- Markdown "## " 헤딩부터 시작하세요.
- 학술 논문 수준의 충분한 분량(2-4 단락 이상)으로 작성하세요. 너무 짧게 쓰지 마세요.
"""

_HEADING_RE = re.compile(r"^##\s+(.*)$", re.M)


def _split_sections(md_text: str) -> list:
    """md_text를 '## ' 헤딩 기준으로 (헤딩 텍스트, 시작 위치, 끝 위치) 리스트로 분할.
    끝 위치는 다음 '## ' 헤딩의 시작 또는 문서 끝."""
    matches = list(_HEADING_RE.finditer(md_text))
    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        blocks.append((m.group(1).strip(), start, end))
    return blocks


class SectionReviewer(BaseAgent):
    """기존 논문에서 표준 섹션이 빠져 있으면 새로 생성하고,
    너무 짧고 부실한 섹션은 기존 내용을 유지하며 확장 재작성한다."""

    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("SectionReviewer", MODEL_WORKER, verbose)
        self.mode = mode

    async def review_and_fill(self, md_text: str, title: str) -> tuple:
        """반환값: (수정된 md_text, 섹션별 처리 리포트 리스트)"""
        if self.mode != "academic":
            self.logger.warning("섹션 검토·보완은 현재 academic 모드만 지원 — 건너뜀")
            return md_text, []

        blocks = _split_sections(md_text)

        matched = {}
        for key, patterns in SECTION_KEYWORDS.items():
            for idx, (heading, _s, _e) in enumerate(blocks):
                if any(re.search(p, heading, re.I) for p in patterns):
                    matched[key] = idx
                    break

        abstract_excerpt = ""
        if "abstract" in matched:
            _h, s, e = blocks[matched["abstract"]]
            abstract_excerpt = md_text[s:e][:500]

        report = []
        edits = []  # (start, end, new_text) — 원본 md_text 오프셋 기준

        for key in CANONICAL_ORDER:
            label = SECTION_LABELS[key]
            min_len = MIN_SECTION_LENGTH[key]

            if key in matched:
                heading, s, e = blocks[matched[key]]
                body = md_text[s:e]
                if len(body) >= min_len:
                    report.append({"section": label, "action": "ok", "length": len(body)})
                    continue
                existing_note = (
                    "이 섹션은 현재 아래와 같이 매우 짧습니다. 기존 내용을 유지하되 "
                    "훨씬 더 충실하게 확장하세요:"
                )
                existing_content = body
                action = "expand"
            else:
                existing_note = "이 섹션은 현재 논문에 없습니다. 새로 작성하세요."
                existing_content = ""
                action = "generate"

            prompt = ENHANCE_SECTION_PROMPT.format(
                title=title, abstract_excerpt=abstract_excerpt,
                existing_note=existing_note, existing_content=existing_content,
                section_label=label,
            )
            content, stop_reason = await self.call_llm(
                ENHANCE_SECTION_SYSTEM, prompt,
                max_tokens=MAX_TOKENS_SECTION, temperature=0.5,
                label=f"enhance_{key}", return_meta=True,
            )
            if stop_reason == "max_tokens":
                self.logger.warning(f"[{label}] 잘림 감지 — 더 큰 토큰 한도로 1회 재시도")
                content, stop_reason = await self.call_llm(
                    ENHANCE_SECTION_SYSTEM, prompt,
                    max_tokens=MAX_TOKENS_SECTION_RETRY_CAP, temperature=0.5,
                    label=f"enhance_{key} (retry)", return_meta=True,
                )
                if stop_reason == "max_tokens":
                    self.logger.warning(f"[{label}] 재시도에도 잘림 — 그대로 사용 (수동 확인 필요)")

            if not content or len(content.strip()) < 30:
                self.logger.warning(f"[{label}] 생성 결과가 비어있거나 매우 짧음 — 건너뜀")
                report.append({"section": label, "action": "failed", "length": len(content or "")})
                continue

            content = content.strip() + "\n\n"

            if key in matched:
                _h, s, e = blocks[matched[key]]
                edits.append((s, e, content))
            else:
                insert_at = None
                for later_key in CANONICAL_ORDER[CANONICAL_ORDER.index(key) + 1:]:
                    if later_key in matched:
                        insert_at = blocks[matched[later_key]][1]
                        break
                if insert_at is None:
                    m = re.search(r"^##\s+(references|참고문헌)", md_text, re.I | re.M)
                    insert_at = m.start() if m else len(md_text)
                edits.append((insert_at, insert_at, content))

            report.append({"section": label, "action": action, "length": len(content)})

        # 같은 위치에 여러 개 삽입될 수 있으므로(빠진 섹션이 연속으로 여러 개인 경우),
        # canonical 순서가 유지되도록 뒤에서부터(원본 위치 내림차순, 동일 위치는 나중
        # canonical 항목부터) 적용한다.
        indexed = list(enumerate(edits))
        indexed.sort(key=lambda t: (t[1][0], t[0]), reverse=True)

        new_md = md_text
        for _orig_idx, (s, e, new_content) in indexed:
            new_md = new_md[:s] + new_content + new_md[e:]

        return new_md, report


class TableGenerator(BaseAgent):
    """기존 논문 본문을 근거로 비교/환경/Ablation 테이블 생성"""

    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("TableGenerator", MODEL_WORKER, verbose)
        self.mode = mode

    async def generate(self, title: str, content: str, metric: str) -> dict:
        prompt = TABLE_PROMPT.format(
            title=title, mode=self.mode, excerpt=content[:3000], m1=metric,
        )
        response, stop_reason = await self.call_llm(
            TABLE_SYSTEM, prompt, max_tokens=2000, temperature=0.3,
            label="enhancer_tables", return_meta=True,
        )
        if stop_reason == "max_tokens":
            self.logger.warning(
                "테이블 생성 응답이 max_tokens=2000에서 잘림 — max_tokens=4000으로 1회 재시도"
            )
            response, stop_reason = await self.call_llm(
                TABLE_SYSTEM, prompt, max_tokens=4000, temperature=0.3,
                label="enhancer_tables (retry)", return_meta=True,
            )
            if stop_reason == "max_tokens":
                self.logger.warning("테이블 생성이 재시도에도 잘림 — 그대로 사용 (수동 확인 필요)")
        tables = self.parse_json(response)
        if not isinstance(tables, dict) or not tables:
            self.logger.warning(
                "테이블 생성 결과가 비어있음 — LLM 응답 JSON 파싱 실패 또는 빈 결과일 가능성 있음"
            )
            return {}
        return tables


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
    """기존 .md 파일을 분석해:
    1) 빠진 표준 섹션을 새로 작성하고 부실한 섹션을 확장 재작성한 뒤,
    2) 그림(아키텍처/성능/Ablation)과 비교 테이블을 자동 추가한다."""

    def __init__(self, mode: str, verbose: bool = False):
        self.mode = mode
        self.figure_builder   = FigureBuilder(mode, verbose)
        self.table_generator  = TableGenerator(mode, verbose)
        self.section_reviewer = SectionReviewer(mode, verbose)
        self.logger = get_logger("PaperEnhancer")

    async def enhance(self, md_path: Path, progress_cb: Optional[Callable[[str], None]] = None) -> dict:
        def report(msg: str):
            if progress_cb:
                progress_cb(msg)

        FIG_DIR.mkdir(parents=True, exist_ok=True)
        original_md_text = md_path.read_text(encoding="utf-8")
        md_text = original_md_text
        title   = _extract_title(md_text)

        # ── 0단계: 섹션 완성도 검토·보완 (빠진 섹션 생성 + 부실한 섹션 재작성) ──
        report("섹션 완성도 검토 중...")
        section_report: list = []
        try:
            md_text, section_report = await self.section_reviewer.review_and_fill(md_text, title)
        except Exception as e:
            self.logger.warning(f"섹션 검토·보완 실패 — 원본 그대로 진행: {e}")

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
            try:
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
                else:
                    self.logger.warning("아키텍처 다이어그램 생성 결과가 비어있음 (png=None)")
            except Exception as e:
                self.logger.warning(f"아키텍처 다이어그램 생성 실패 — 이 그림 없이 계속 진행: {e}")

        # ── 2단계: 테이블 변환 중 (LLM 테이블 생성 → 차트 변환) ────
        report("테이블 변환 중...")
        tables: dict = {}
        if not has_results_section:
            try:
                tables = await self.table_generator.generate(title, md_text, metric)
            except Exception as e:
                self.logger.warning(f"테이블 생성 실패 — 표/차트 없이 계속 진행: {e}")
                tables = {}
        state.experiment_tables = tables

        if not has_figures_section:
            if tables.get("model_comparison"):
                try:
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
                except Exception as e:
                    self.logger.warning(f"성능 비교 차트 생성 실패 — 이 그림 없이 계속 진행: {e}")
            if tables.get("ablation"):
                try:
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
                except Exception as e:
                    self.logger.warning(f"Ablation 차트 생성 실패 — 이 그림 없이 계속 진행: {e}")

        # ── 3단계: 완료 (문서 병합 & 저장) ─────────────────────────
        report("문서 병합 중...")
        new_md = md_text
        if tables and not has_results_section:
            new_md = _insert_before_references(new_md, _tables_to_markdown(tables))
        if figures and not has_figures_section:
            new_md = _insert_before_references(new_md, _figures_to_markdown(figures))

        if new_md != original_md_text:
            md_path.write_text(new_md, encoding="utf-8")

        report("완료")
        return {
            "md_text": new_md, "figures": figures, "tables": tables,
            "path": str(md_path), "section_report": section_report,
        }
