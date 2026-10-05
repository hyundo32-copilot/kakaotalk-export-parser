import pytest

from kakao_export_parser import parse_text, extract_demo


SAMPLE = """테스트방과 카카오톡 대화
저장한 날짜 : 2026-10-05 13:00:00

--------------- 2026년 10월 1일 수요일 ---------------
[김모임] [오후 7:01] 안녕하세요
[이등산] [오후 7:05] 10월 18일로 정했어요
계속 이어지는 둘째 줄
[박산행] [오전 9:13] 사진
[박산행] [오전 9:14] 파일: 코스지도.pdf
[김모임] [오후 12:00] 정오 테스트
이등산님이 나갔습니다.
"""


def test_header_and_saved_at():
    chat = parse_text(SAMPLE)
    assert chat.title == "테스트방"
    assert chat.saved_at == "2026-10-05 13:00:00"


def test_message_count_and_order():
    chat = parse_text(SAMPLE)
    # 텍스트 5 + 시스템 1 = 6개
    assert len(chat.messages) == 6
    assert [m.seq for m in chat.messages] == [1, 2, 3, 4, 5, 6]


def test_time_conversion():
    chat = parse_text(SAMPLE)
    by_seq = {m.seq: m for m in chat.messages}
    assert by_seq[1].time == "19:01"   # 오후 7:01
    assert by_seq[3].time == "09:13"   # 오전 9:13
    assert by_seq[5].time == "12:00"   # 오후 12:00 (정오)


def test_multiline_body():
    chat = parse_text(SAMPLE)
    m2 = chat.messages[1]
    assert m2.text == "10월 18일로 정했어요\n계속 이어지는 둘째 줄"


def test_media_kinds():
    chat = parse_text(SAMPLE)
    by_seq = {m.seq: m for m in chat.messages}
    assert by_seq[3].kind == "photo" and by_seq[3].text is None
    assert by_seq[4].kind == "file" and by_seq[4].file_name == "코스지도.pdf"


def test_system_message():
    chat = parse_text(SAMPLE)
    m6 = chat.messages[5]
    assert m6.system is True
    assert m6.kind == "system"


def test_msg_hash_dedup_key():
    chat = parse_text(SAMPLE)
    hashes = [m.msg_hash for m in chat.messages]
    assert all(h for h in hashes)
    assert len(set(hashes)) == len(hashes)


def test_decision_notes_demo():
    chat = parse_text(SAMPLE)
    notes = extract_demo(chat)
    kinds = {n.kind for n in notes}
    # "10월 18일로 정했어요" → decision + date 힌트
    assert "decision" in kinds or "date" in kinds
    for n in notes:
        assert n.confidence == 0.5
        assert n.extractor == "rule-demo-v0"
