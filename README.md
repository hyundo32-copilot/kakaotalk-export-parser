# kakaotalk-export-parser

카카오톡 **대화 내보내기(.txt)** 파일을 파싱해 구조화된 메시지 리스트로 변환하는 프로토타입입니다.

「흩어진 단톡방 대화를 결정 노트로 만드는 AI 비서」(2026 모두의 AI 실험실 지원 프로젝트)의
**수집 모듈**에 해당합니다. 대화 내보내기는 과거 대화와 본인 메시지까지 한 번에 확보할 수 있어
1순위 수집 경로로 채택했습니다.

## 할 수 있는 것

- 헤더(방 제목·저장 날짜), 날짜 구분선 파싱
- 메시지 파싱: `[이름] [오후 7:01] 내용` → 발신자·시간(24h)·본문
- 멀티라인 메시지 (접두사 없는 이어지는 줄을 직전 메시지에 병합)
- 미디어 플레이스홀더: 사진·동영상·이모티콘·음성메시지·파일(`파일: xxx`)
- 시스템 메시지: 입장·퇴장·초대
- `msg_hash`: `sha256(방|날짜|시간|발신자|종류|본문)` — DB 중복 제거 키
- 인코딩 자동 판별 (utf-8 → utf-8-sig → euc-kr)

## 결정 노트 데모

`decision_notes.py`는 규칙 기반의 **동작 확인용 데모**입니다. 실제 서비스에서는 LLM이
대화 맥락을 읽고 결정·할일·날짜를 추출합니다. 규칙 기반 결과는 오탐/누락이 있을 수 있으며,
출력 스키마(shape) 확인용으로만 사용하세요.

## 사용법

```bash
pip install -e .
pytest

# 파싱 결과 JSON
kakao-export-parse samples/sample_chat.txt

# 결정 노트 데모 포함
kakao-export-parse samples/sample_chat.txt --notes
```

## 출력 예시

`samples/sample_decision_notes.json` 참고.

## 스키마

```jsonc
// 메시지
{ "seq": 1, "date": "2026-10-01", "time": "19:01", "sender": "김모임",
  "kind": "text", "text": "...", "file_name": null, "system": false,
  "msg_hash": "a1b2..." }
// 결정 노트
{ "kind": "decision | todo | date", "summary": "한 줄 요약",
  "detail": null, "decided_at": "10월 18일",
  "source_seq": [4], "confidence": 0.5, "extractor": "rule-demo-v0" }
```

## 샘플 데이터

`samples/sample_chat.txt`는 파서 테스트용으로 만든 **가상의 대화**입니다. 실존 인물·단체와 무관합니다.

## 라이선스

MIT
