"""카카오톡 '대화 내보내기' 텍스트 파서.

카카오톡 대화방에서 [더보기 > 대화 내용 > 대화 내보내기]로 저장한 .txt 파일을
구조화된 메시지 리스트로 변환한다. 멀티라인 메시지, 미디어 플레이스홀더,
입장/퇴장/초대 시스템 메시지를 처리한다.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path


_HEADER_RE = re.compile(r"^(?P<title>.+?)(님과|와|과) 카카오톡 대화\s*$")
_SAVED_AT_RE = re.compile(r"^저장한 날짜\s*:\s*(?P<ts>.+?)\s*$")
_DATE_SEP_RE = re.compile(
    r"^-+\s*(?P<year>\d{4})년\s*(?P<month>\d{1,2})월\s*(?P<day>\d{1,2})일.*?-+\s*$"
)
_MSG_RE = re.compile(
    r"^\[(?P<sender>[^\]]+)\]\s*"
    r"\[(?P<ampm>오전|오후)\s*(?P<hour>\d{1,2}):(?P<minute>\d{2})\]\s?"
    r"(?P<body>.*)$"
)
_SYSTEM_RES = [
    re.compile(r"^(?P<who>.+?)님이 (나갔습니다|들어왔습니다)\.\s*$"),
    re.compile(r"^(?P<who>.+?)님을 초대했습니다\.\s*$"),
    re.compile(r"^(?P<who>.+?)님이 채팅방을 나갔습니다\.\s*$"),
]
# 본문이 정확히 일치하면 미디어 메시지로 분류
_MEDIA_EXACT = {
    "사진": "photo",
    "동영상": "video",
    "이모티콘": "emoticon",
    "음성메시지": "voice",
    "지도": "map",
}


@dataclass
class Message:
    seq: int
    date: str            # YYYY-MM-DD
    time: str            # HH:MM (24h)
    sender: str
    kind: str            # text | photo | video | emoticon | voice | file | map | system
    text: str | None     # text/file이면 내용, 미디어 단독이면 None
    file_name: str | None = None
    system: bool = False
    msg_hash: str = ""   # sha256(title|date|time|sender|kind|text) — 중복 제거 키

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChatExport:
    title: str
    saved_at: str | None
    messages: list[Message] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "saved_at": self.saved_at,
            "message_count": len(self.messages),
            "messages": [m.to_dict() for m in self.messages],
        }


def _to_24h(ampm: str, hour: int, minute: int) -> str:
    if ampm == "오전":
        h = 0 if hour == 12 else hour
    else:
        h = 12 if hour == 12 else hour + 12
    return f"{h:02d}:{minute:02d}"


def _classify_body(body: str) -> tuple[str, str | None, str | None]:
    """(kind, text, file_name) 반환."""
    body = body.strip()
    if body in _MEDIA_EXACT:
        return _MEDIA_EXACT[body], None, None
    if body.startswith("파일:"):
        return "file", None, body[len("파일:"):].strip() or None
    return "text", body, None


def _is_system(line: str) -> bool:
    return any(r.match(line) for r in _SYSTEM_RES)


def parse_text(raw: str) -> ChatExport:
    title = ""
    saved_at = None
    messages: list[Message] = []
    cur_date = ""
    current: Message | None = None
    seq = 0

    def flush() -> None:
        nonlocal current
        if current is not None:
            current.msg_hash = hashlib.sha256(
                "|".join([
                    title, current.date, current.time,
                    current.sender, current.kind, current.text or "",
                ]).encode("utf-8")
            ).hexdigest()[:16]
            messages.append(current)
            current = None

    for raw_line in raw.splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue
        if not title:
            m = _HEADER_RE.match(line.strip())
            if m:
                title = m.group("title")
                continue
        if saved_at is None:
            m = _SAVED_AT_RE.match(line.strip())
            if m:
                saved_at = m.group("ts")
                continue
        m = _DATE_SEP_RE.match(line.strip())
        if m:
            flush()
            cur_date = f"{int(m.group('year')):04d}-{int(m.group('month')):02d}-{int(m.group('day')):02d}"
            continue
        m = _MSG_RE.match(line)
        if m and cur_date:
            flush()
            seq += 1
            kind, text, file_name = _classify_body(m.group("body"))
            current = Message(
                seq=seq,
                date=cur_date,
                time=_to_24h(m.group("ampm"), int(m.group("hour")), int(m.group("minute"))),
                sender=m.group("sender"),
                kind=kind,
                text=text,
                file_name=file_name,
            )
            continue
        if _is_system(line.strip()):
            flush()
            seq += 1
            current = Message(
                seq=seq, date=cur_date, time="", sender="",
                kind="system", text=line.strip(), system=True,
            )
            flush()
            continue
        # 접두사가 없으면 직전 메시지의 이어지는 줄(멀티라인)
        if current is not None and current.kind in ("text", "file"):
            current.text = (current.text or "") + "\n" + line
        # else: 해석 불가 줄은 무시
    flush()
    return ChatExport(title=title, saved_at=saved_at, messages=messages)


def parse_file(path: str | Path, encoding: str = "utf-8") -> ChatExport:
    # 카카오톡 내보내기는 보통 UTF-8. 깨지면 utf-8-sig / euc-kr 순으로 재시도
    p = Path(path)
    for enc in (encoding, "utf-8-sig", "euc-kr"):
        try:
            return parse_text(p.read_text(encoding=enc))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"인코딩을 판별할 수 없습니다: {path}")
