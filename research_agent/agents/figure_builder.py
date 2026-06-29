# agents/figure_builder.py
# 성능 비교 차트 자동 생성 (matplotlib → PNG bytes)

import io
import re
from core.base_agent import BaseAgent
from core.state import ResearchState
from config.settings import MODEL_WORKER


class FigureBuilder(BaseAgent):
    def __init__(self, mode: str, verbose: bool = False):
        super().__init__("FigureBuilder", MODEL_WORKER, verbose)
        self.mode = mode

    def build(self, state: ResearchState) -> list[dict]:
        figures = []

        tables = state.experiment_tables
        metrics = state.experiment.get("metrics", ["Accuracy"])

        # Figure 1: 모델 성능 비교 바 차트
        mc = tables.get("model_comparison", "")
        if mc:
            png = self._bar_chart(mc, metrics[0] if metrics else "Score", state.topic)
            if png:
                figures.append({
                    "title": "Figure 1: Model Performance Comparison",
                    "caption": f"Comparison of proposed method vs. baselines on {metrics[0] if metrics else 'primary metric'}.",
                    "png_bytes": png,
                })

        # Figure 2: Ablation Study 바 차트
        abl = tables.get("ablation", "")
        if abl:
            metric_label = metrics[0] if metrics else "Score"
            png = self._ablation_chart(abl, metric_label, state.topic)
            if png:
                figures.append({
                    "title": "Figure 2: Ablation Study",
                    "caption": "Impact of each proposed component on model performance.",
                    "png_bytes": png,
                })

        if figures:
            self.print_status(f"그림 {len(figures)}개 생성 완료")
        return figures

    # ── 내부 헬퍼 ───────────────────────────────────────────────

    def _parse_table(self, md_table: str) -> tuple[list[str], list[list[str]]]:
        lines = [l.strip() for l in md_table.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            return [], []
        headers = [h.strip() for h in lines[0].split("|") if h.strip()]
        rows = []
        for line in lines[2:]:
            cells = [c.strip() for c in line.split("|") if c.strip()]
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

    def _bar_chart(self, md_table: str, metric_label: str, topic: str) -> bytes | None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np

            headers, rows = self._parse_table(md_table)
            if not rows or len(headers) < 2:
                return None

            # 첫 번째 수치 열 찾기
            metric_col = 1
            models, values = [], []
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

            # 색상: 제안 방법 강조
            colors = []
            for m in models:
                lm = m.lower()
                if any(k in lm for k in ("proposed", "ours", "our")):
                    colors.append("#FF6B35")
                else:
                    colors.append("#144FA8")

            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(range(len(models)), values, color=colors,
                          alpha=0.85, edgecolor="white", linewidth=1.2)

            ax.set_xticks(range(len(models)))
            ax.set_xticklabels(models, rotation=20, ha="right", fontsize=9)
            ax.set_ylabel(metric_label, fontsize=10)

            short = topic[:45] + ("…" if len(topic) > 45 else "")
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
            legend = [Patch(color="#FF6B35", label="Proposed"), Patch(color="#144FA8", label="Baseline / SOTA")]
            ax.legend(handles=legend, fontsize=8, loc="lower right")

            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()

        except Exception as e:
            self.logger.warning(f"Bar chart 생성 실패: {e}")
            return None

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
                        labels.append(r[0][:20])
                        values.append(v)
                        break

            if not labels:
                return None

            colors = ["#FF6B35"] + ["#144FA8"] * (len(labels) - 1)
            fig, ax = plt.subplots(figsize=(7, 4))
            bars = ax.barh(range(len(labels)), values, color=colors, alpha=0.85,
                           edgecolor="white", linewidth=1.0)

            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels, fontsize=9)
            ax.set_xlabel(metric_label, fontsize=10)
            ax.set_title("Ablation Study", fontsize=11, fontweight="bold")

            for bar, val in zip(bars, values):
                ax.text(val + max(values) * 0.005, bar.get_y() + bar.get_height() / 2,
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
