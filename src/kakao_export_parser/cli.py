"""간단 CLI: 파싱 결과와 결정 노트 데모를 JSON으로 출력."""
import argparse
import json
import sys

from kakao_export_parser import parse_file, extract_demo, notes_to_json


def main() -> None:
    ap = argparse.ArgumentParser(description="카카오톡 대화 내보내기 파서")
    ap.add_argument("path", help="대화 내보내기 .txt 파일")
    ap.add_argument("--notes", action="store_true", help="결정 노트 데모 추출 결과도 출력")
    args = ap.parse_args()

    chat = parse_file(args.path)
    out = {"chat": chat.to_dict()}
    if args.notes:
        out["decision_notes_demo"] = json.loads(notes_to_json(extract_demo(chat)))
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
