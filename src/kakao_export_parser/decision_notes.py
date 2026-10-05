"""결정 노트 추출 데모 (규칙 기반).

주의: 이것은 파서 동작을 보여주기 위한 최소 데모다. 실제 서비스에서는
LLM이 대화 맥락을 읽고 결정·할일·날짜를 추출한다. 규칙 기반 결과는
오탐/누락이 많을 수 있으며, 스키마(shape) 확인용으로만 쓴다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict

from .parser import ChatExport

DATE_RES = [
    re.compile(r"\d{1,2}월\s*\d{1,2}일"),
    re.compile(r"(다음|이번|다다음)\s*주\s*([월화수목금토일]요일)?"),
    re.compile(r"(내일|모레|오늘|이번\s*주말|다음\s*주말)"),
    re.compile(r"[월화수목금토일]요일"),
]
DECISION_HINTS = ["로 정했", "으로 정했", "하기로 했", "확정", "결정됐", "결정했", "픽스"]
TODO_HINTS = ["해줘", "해줄래", "부탁", "해야", "할게", "할게요", "준비해", "맡아줘", "챙겨줘"]


@dataclass
class DecisionNote:
    kind: str          # decision | todo | date
    summary: str
    detail: str | None
    decided_at: str | None
    source_seq: list[int]
    confidence: float  # 데모는 0.5 고정
    extractor: str = "rule-demo-v0"

    def to_dict(self) -> dict:
        return asdict(self)


def _has_date(text: str) -> str | None:
    for r in DATE_RES:
        m = r.search(text)
        if m:
            return m.group(0)
    return None


def extract_demo(chat: ChatExport, max_summary_len: int = 60) -> list[DecisionNote]:
    notes: list[DecisionNote] = []
    seen: set[tuple[str, str]] = set()
    for msg in chat.messages:
        if msg.system or msg.kind != "text" or not msg.text:
            continue
        text = msg.text.replace("\n", " ").strip()
        if not text:
            continue
        summary = text if len(text) <= max_summary_len else text[:max_summary_len] + "…"
        date_hit = _has_date(text)
        kind = None
        if any(h in text for h in DECISION_HINTS):
            kind = "decision"
        elif any(h in text for h in TODO_HINTS):
            kind = "todo"
        elif date_hit:
            kind = "date"
        if kind is None:
            continue
        key = (kind, summary)
        if key in seen:
            continue
        seen.add(key)
        notes.append(DecisionNote(
            kind=kind,
            summary=summary,
            detail=None,
            decided_at=date_hit,
            source_seq=[msg.seq],
            confidence=0.5,
        ))
    return notes


def notes_to_json(notes: list[DecisionNote]) -> str:
    return json.dumps([n.to_dict() for n in notes], ensure_ascii=False, indent=2)
