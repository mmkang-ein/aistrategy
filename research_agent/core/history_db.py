# core/history_db.py
# 연구 이력 SQLite DB 관리

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from config.settings import BASE_DIR

DB_PATH = BASE_DIR / "research_history.db"


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS research_history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                topic         TEXT    NOT NULL,
                mode          TEXT    NOT NULL,
                created_at    TEXT    NOT NULL,
                score         REAL,
                output_path   TEXT,
                duration_sec  INTEGER,
                status        TEXT    DEFAULT 'completed'
            )
        """)


def save_research(topic: str, mode: str, score: float | None,
                  output_path: str, duration_sec: int):
    with _conn() as c:
        c.execute("""
            INSERT INTO research_history
                (topic, mode, created_at, score, output_path, duration_sec)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (topic, mode, datetime.now().isoformat(), score, output_path, duration_sec))


def get_all_history(limit: int = 100) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT * FROM research_history ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


# ── 유사도 체크 ──────────────────────────────────────────────────

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "to",
    "with", "vs", "versus", "using", "based", "deep", "learning",
    "survey", "review", "study", "paper", "research", "approach",
    "method", "model", "comparison", "classification", "analysis",
    "연구", "분석", "비교", "관한", "대한", "기반", "활용", "개선",
    "논문", "방법", "모델", "분류", "조사", "리뷰",
}


def _tokenize(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z가-힣]+", text.lower()))
    return tokens - _STOPWORDS


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def find_similar(topic: str, threshold: float = 0.35) -> list[dict]:
    """기존 이력 중 Jaccard 유사도 threshold 이상인 항목 반환 (유사도 내림차순)"""
    history = get_all_history()
    results = []
    for row in history:
        sim = _jaccard(topic, row["topic"])
        if sim >= threshold:
            results.append({**row, "similarity": round(sim, 2)})
    return sorted(results, key=lambda x: -x["similarity"])


# 모듈 임포트 시 자동 초기화
init_db()
