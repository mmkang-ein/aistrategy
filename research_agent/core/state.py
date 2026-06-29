# core/state.py
# 에이전트 간 공유되는 연구 상태 객체

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ResearchState:
    mode:  str = ""
    topic: str = ""

    # Stage 1
    plan: dict = field(default_factory=dict)

    # Stage 2
    raw_sources: list = field(default_factory=list)
    summaries:   list = field(default_factory=list)

    # Stage 3
    ideas:         list = field(default_factory=list)
    selected_idea: dict = field(default_factory=dict)

    # Stage 4
    experiment:   dict = field(default_factory=dict)
    code_snippet: str  = ""

    # Stage 5
    reviews: list = field(default_factory=list)

    # Stage 6
    references:       list = field(default_factory=list)
    section_documents: dict = field(default_factory=dict)   # {section_name: content}
    experiment_tables: dict = field(default_factory=dict)   # {table_name: md_str}
    figures:          list = field(default_factory=list)    # [{title, caption, png_bytes}]
    final_document:   str = ""
    output_path:      str = ""

    # 메타
    started_at:  Optional[datetime] = None
    finished_at: Optional[datetime] = None
    revision_count: int = 0

    def to_dict(self) -> dict:
        return {
            "mode":  self.mode,
            "topic": self.topic,
            "plan":  self.plan,
            "sources_count":  len(self.raw_sources),
            "summaries_count": len(self.summaries),
            "ideas_count":     len(self.ideas),
            "selected_idea":   self.selected_idea,
            "experiment":      self.experiment,
            "reviews":         self.reviews,
            "revision_count":  self.revision_count,
            "output_path":     self.output_path,
            "started_at":  str(self.started_at),
            "finished_at": str(self.finished_at),
        }
