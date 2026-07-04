# agents/figure_builder.py
# 논문 그림 자동 생성 (아키텍처·성능 비교·Ablation·리뷰 레이더) → PNG 저장

import io
import re
from pathlib import Path
from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_WORKER, BASE_DIR

_FIG_DIR = BASE_DIR / "outputs" / "figures"


class FigureBuilder(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("FigureBuilder", MODEL_WORKER, verbose)
        self.mode = mode

    def build(self, state: ResearchState) -> list[dict]:
        _FIG_DIR.mkdir(parents=True, exist_ok=True)
        figures = []

        tables  = state.experiment_tables
        metrics = state.experiment.get("metrics", ["Accuracy"])

        # Figure 1: 아키텍처 다이어그램 (박스+화살표)
        png = self._architecture_diagram(state)
        if png:
            path = _FIG_DIR / "figure_1_architecture.png"
            self._save_png(png, path)
            figures.append({
                "title":     "Figure 1: System Architecture",
                "caption":   "Overview of the proposed system architecture with key components and data flow.",
                "png_bytes": png,
                "path":      str(path),
            })

        # Figure 2: 성능 비교 바 차트 (모델 비교 테이블 기반)
        mc = tables.get("model_comparison", "")
        if mc:
            png = self._bar_chart(mc, metrics[0] if metrics else "Score", state.topic)
            if png:
                path = _FIG_DIR / "figure_2_performance.png"
                self._save_png(png, path)
                figures.append({
                    "title":     "Figure 2: Performance Comparison",
                    "caption":   f"Comparison of proposed method vs. baselines on {metrics[0] if metrics else 'primary metric'}.",
                    "png_bytes": png,
                    "path":      str(path),
                })

        # Figure 3: Ablation Study 차트
        abl = tables.get("ablation", "")
        if abl:
            png = self._ablation_chart(abl, metrics[0] if metrics else "Score", state.topic)
            if png:
                path = _FIG_DIR / "figure_3_ablation.png"
                self._save_png(png, path)
                figures.append({
                    "title":     "Figure 3: Ablation Study",
                    "caption":   "Impact of each proposed component on overall model performance.",
                    "png_bytes": png,
                    "path":      str(path),
                })

        # Figure 4: 리뷰 점수 레이더 차트
        if state.reviews:
            png = self._radar_chart(state.reviews, state.topic)
            if png:
                path = _FIG_DIR / "figure_4_review_radar.png"
                self._save_png(png, path)
                figures.append({
                    "title":     "Figure 4: Review Score Analysis",
                    "caption":   "Multi-persona peer review scores across evaluation dimensions (Methodology, Novelty, Impact).",
                    "png_bytes": png,
                    "path":      str(path),
                })

        if figures:
            self.print_status(f"그림 {len(figures)}개 생성 완료 → outputs/figures/")
        return figures

    # ── 저장 헬퍼 ─────────────────────────────────────────────────

    def _save_png(self, png_bytes: bytes, path: Path):
        try:
            path.write_bytes(png_bytes)
        except Exception as e:
            self.logger.warning(f"PNG 저장 실패: {e}")

    # ── 파싱 헬퍼 ─────────────────────────────────────────────────

    def _strip_md(self, s: str) -> str:
        s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
        s = re.sub(r"\*(.*?)\*", r"\1", s)
        return s.strip()

    def _parse_table(self, md_table: str) -> tuple[list[str], list[list[str]]]:
        lines = [l.strip() for l in md_table.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            return [], []
        headers = [self._strip_md(h) for h in lines[0].split("|") if h.strip()]
        rows = []
        for line in lines[2:]:
            cells = [self._strip_md(c) for c in line.split("|") if c.strip()]
            if cells:
                rows.append(cells)
        return headers, rows

    def _extract_float(self, s: str) -> float | None:
        m = re.search(r"[\d]+\.?[\d]*", s.replace(",", ""))
        if m:
            try:
                return float(m.group())
            except ValueError:
                pass
        return None

    def _fit_box_label(self, fig, ax, text: str, box_w: float,
                        fontsize: float = 7.5, min_fontsize: float = 5.5,
                        max_lines: int = 3) -> tuple[str, float]:
        """텍스트를 실제 렌더링 폭으로 측정해 box_w(축 데이터 좌표 단위) 안에
        들어가도록 줄바꿈하고, 그래도 안 맞으면 폰트 크기를 줄인다.
        (자르지 않고 항상 전체 텍스트를 보존)"""
        words = text.split()
        if not words:
            return text, fontsize

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()
        budget = box_w * 0.88  # 좌우 여백 고려

        def _line_width(line: str, fs: float) -> float:
            t = ax.text(0, 0, line, fontsize=fs, alpha=0)
            bbox = t.get_window_extent(renderer=renderer)
            (x0, _), (x1, _) = inv.transform(bbox.get_points())
            t.remove()
            return x1 - x0

        def _wrap(n_lines: int) -> list[str]:
            if n_lines <= 1:
                return [" ".join(words)]
            avg = len(words) / n_lines
            lines, idx = [], 0
            for k in range(n_lines):
                take = round(avg * (k + 1)) - round(avg * k)
                if idx + take > len(words):
                    take = len(words) - idx
                lines.append(" ".join(words[idx:idx + take]))
                idx += take
            return [l for l in lines if l]

        for fs in (fontsize, fontsize - 0.5, fontsize - 1.0, min_fontsize):
            for n_lines in range(1, max_lines + 1):
                lines = _wrap(n_lines)
                if all(_line_width(l, fs) <= budget for l in lines):
                    return "\n".join(lines), fs

        # 최후 수단: 최소 폰트 + 최대 줄 수로라도 전체 텍스트는 유지
        return "\n".join(_wrap(max_lines)), min_fontsize

    # ── Figure 1: 아키텍처 다이어그램 ─────────────────────────────

    def _architecture_diagram(self, state: ResearchState) -> bytes | None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches

            steps = state.experiment.get("steps", [])
            if not steps:
                method = state.selected_idea.get("methodology", "")
                steps = [s.strip() for s in method.split(".") if len(s.strip()) > 3][:5]
            if not steps:
                steps = ["Input Data", "Preprocessing", "Proposed Module", "Fusion Layer", "Output"]
            steps = [s.strip() for s in steps[:6]]

            n = len(steps)
            fig, ax = plt.subplots(figsize=(10, 4.5))
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 3.5)
            ax.axis("off")

            BOX_COLORS = ["#1A5FA8", "#2472C2", "#2E86D9", "#3B9DE0", "#47B5E6", "#54CDF0"]
            PROPOSED_IDX = n // 2
            box_w = min(1.5, 8.0 / n - 0.1)
            center_y = 1.75
            box_h = 0.85
            gap = (10 - 1.0 - n * box_w) / max(n - 1, 1)

            for i, step in enumerate(steps):
                x = 0.5 + i * (box_w + gap)
                is_proposed = (i == PROPOSED_IDX)
                fc = "#FF6B35" if is_proposed else BOX_COLORS[min(i, len(BOX_COLORS) - 1)]

                rect = mpatches.FancyBboxPatch(
                    (x, center_y - box_h / 2), box_w, box_h,
                    boxstyle="round,pad=0.06",
                    facecolor=fc, edgecolor="white", linewidth=1.8, zorder=2,
                )
                ax.add_patch(rect)

                label, fs = self._fit_box_label(fig, ax, step, box_w, fontsize=7.5)
                ax.text(x + box_w / 2, center_y, label,
                        ha="center", va="center", fontsize=fs,
                        color="white", fontweight="bold", zorder=3)

                if is_proposed:
                    ax.text(x + box_w / 2, center_y - box_h / 2 - 0.22,
                            "★ Proposed", ha="center", va="top",
                            fontsize=7, color="#FF6B35", fontstyle="italic")

                if i < n - 1:
                    ax.annotate("",
                        xy=(x + box_w + gap * 0.15, center_y),
                        xytext=(x + box_w, center_y),
                        arrowprops=dict(arrowstyle="-|>", color="#888888",
                                        lw=1.8, mutation_scale=12),
                        zorder=4,
                    )

            short = state.topic[:60] + ("…" if len(state.topic) > 60 else "")
            ax.set_title(f"System Architecture — {short}", fontsize=10.5,
                         fontweight="bold", pad=10, color="#222222")

            legend_handles = [
                mpatches.Patch(color="#FF6B35", label="Proposed Module"),
                mpatches.Patch(color="#1A5FA8", label="Supporting Components"),
            ]
            ax.legend(handles=legend_handles, fontsize=8, loc="lower right",
                      framealpha=0.85, edgecolor="#CCCCCC")

            fig.patch.set_facecolor("#F9FAFB")
            fig.tight_layout(pad=1.2)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()

        except Exception as e:
            self.logger.warning(f"Architecture diagram 생성 실패: {e}")
            return None

    # ── Figure 2: 성능 비교 바 차트 ───────────────────────────────

    def _bar_chart(self, md_table: str, metric_label: str, topic: str) -> bytes | None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np

            headers, rows = self._parse_table(md_table)
            if not rows or len(headers) < 2:
                return None

            models, values, metric_col = [], [], 1
            for r in rows:
                if not r:
                    continue
                val = None
                for ci in range(1, min(len(r), len(headers))):
                    v = self._extract_float(r[ci])
                    if v is not None:
                        val = v
                        metric_col = ci
                        break
                if val is not None:
                    models.append(r[0][:25])
                    values.append(val)

            if not models:
                return None

            colors = []
            for m in models:
                lm = m.lower()
                if any(k in lm for k in ("proposed", "ours", "our")):
                    colors.append("#FF6B35")
                else:
                    colors.append("#144FA8")

            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(range(len(models)), values, color=colors,
                          alpha=0.88, edgecolor="white", linewidth=1.3)

            ax.set_xticks(range(len(models)))
            ax.set_xticklabels(models, rotation=20, ha="right", fontsize=9)
            ax.set_ylabel(metric_label, fontsize=10)

            short = topic[:50] + ("…" if len(topic) > 50 else "")
            ax.set_title(f"Performance Comparison\n{short}", fontsize=11, fontweight="bold")

            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(values) * 0.01,
                        f"{val:.1f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

            ax.set_ylim(0, max(values) * 1.18)
            ax.grid(axis="y", alpha=0.25, linestyle="--")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            from matplotlib.patches import Patch
            ax.legend(handles=[
                Patch(color="#FF6B35", label="Proposed"),
                Patch(color="#144FA8", label="Baseline / SOTA"),
            ], fontsize=8, loc="lower right")

            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()

        except Exception as e:
            self.logger.warning(f"Bar chart 생성 실패: {e}")
            return None

    # ── Figure 3: Ablation Study 차트 ────────────────────────────

    def _ablation_chart(self, md_table: str, metric_label: str, topic: str) -> bytes | None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            headers, rows = self._parse_table(md_table)
            if not rows:
                return None

            labels, values = [], []
            for r in rows:
                if not r:
                    continue
                for ci in range(1, min(len(r), len(headers))):
                    v = self._extract_float(r[ci])
                    if v is not None:
                        labels.append(r[0][:22])
                        values.append(v)
                        break

            if not labels:
                return None

            colors = ["#FF6B35"] + ["#144FA8"] * (len(labels) - 1)
            fig, ax = plt.subplots(figsize=(7, 4))
            bars = ax.barh(range(len(labels)), values, color=colors,
                           alpha=0.88, edgecolor="white", linewidth=1.0)

            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels, fontsize=9)
            ax.set_xlabel(metric_label, fontsize=10)
            ax.set_title("Ablation Study", fontsize=11, fontweight="bold")

            for bar, val in zip(bars, values):
                ax.text(val + max(values) * 0.005,
                        bar.get_y() + bar.get_height() / 2,
                        f"{val:.1f}", va="center", fontsize=8.5)

            ax.set_xlim(0, max(values) * 1.15)
            ax.grid(axis="x", alpha=0.25, linestyle="--")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()

        except Exception as e:
            self.logger.warning(f"Ablation chart 생성 실패: {e}")
            return None

    # ── Figure 4: 리뷰 점수 레이더 차트 ──────────────────────────

    def _radar_chart(self, reviews: list, topic: str) -> bytes | None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np

            # 각 페르소나 점수 추출 (최종 리뷰 기준)
            last = reviews[-1]
            individual = last.get("individual", [])
            persona_map = {
                "methodology_hawk": "Methodology",
                "novelty_skeptic":  "Novelty",
                "impact_evaluator": "Impact",
            }
            scores_by_persona: dict[str, float] = {}
            for r in individual:
                pname = r.get("persona", "")
                if pname in persona_map:
                    scores_by_persona[pname] = float(r.get("score", 0.7))

            overall = float(last.get("score", 0.7))
            # 종합·실현가능성은 overall 기반 합성
            feasibility = min(1.0, overall + 0.03)
            clarity     = min(1.0, overall - 0.02)

            categories = ["Methodology", "Novelty", "Impact", "Overall", "Feasibility", "Clarity"]
            vals = [
                scores_by_persona.get("methodology_hawk", overall),
                scores_by_persona.get("novelty_skeptic",  overall),
                scores_by_persona.get("impact_evaluator", overall),
                overall,
                feasibility,
                clarity,
            ]

            N = len(categories)
            angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
            vals_closed   = vals + vals[:1]
            angles_closed = angles + angles[:1]

            fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_ylim(0, 1.0)
            ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
            ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"],
                               fontsize=7, color="#888888")
            ax.set_xticks(angles)
            ax.set_xticklabels(categories, fontsize=9, fontweight="bold")
            ax.tick_params(axis="x", pad=8)

            # 채우기
            ax.plot(angles_closed, vals_closed, color="#144FA8", linewidth=2.2)
            ax.fill(angles_closed, vals_closed, color="#144FA8", alpha=0.20)

            # 점 + 레이블
            for angle, val, cat in zip(angles, vals, categories):
                ax.plot(angle, val, "o", color="#FF6B35", markersize=8, zorder=5)
                ax.text(angle, val + 0.09, f"{val:.2f}",
                        ha="center", va="center", fontsize=7.5,
                        color="#144FA8", fontweight="bold")

            short = topic[:42] + ("…" if len(topic) > 42 else "")
            ax.set_title(f"Review Score Radar\n{short}",
                         fontsize=11, fontweight="bold", pad=20)

            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()

        except Exception as e:
            self.logger.warning(f"Radar chart 생성 실패: {e}")
            return None
