"""PIMS 클라이언트 사용 예제.

실행 전에:
    1) cp .env.example .env  후 .env 에 인증 정보 입력
    2) pip install -r requirements.txt
    3) python example_usage.py

실행 결과를 보는 곳:
    - 터미널 화면 (콘솔 출력)
    - pims.log        : 모든 요청/응답 로그
    - output/*.json   : 조회한 데이터 (tags.json, subsystems.json ...)
"""

import json
from pathlib import Path

from pims_client import PimsError, build_client_from_env, setup_logging

OUTPUT_DIR = Path("output")


def save(name: str, data) -> None:
    """조회 결과를 output/<name>.json 으로 저장합니다."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장됨 → {path}")


def main() -> None:
    # 콘솔 + pims.log 파일로 로그 출력 설정
    setup_logging(logfile="pims.log")

    # .env 를 읽어 환경변수 기반으로 클라이언트 생성
    client = build_client_from_env()

    try:
        # ---------------- 조회 (GET) ----------------
        # 필터/페이징 파라미터는 키워드 인자로 전달합니다.
        # (실제 파라미터명은 PIMS 문서 기준으로 맞추세요. 예: page, size, subsystem 등)
        print("[1] Tags 조회")
        tags = client.get_tags(page=1, size=20)
        save("tags", tags)

        print("[2] SubSystems 조회")
        subsystems = client.get_subsystems()
        save("subsystems", subsystems)

        print("[3] ITR(tagevents) 조회")
        itrs = client.get_itrs(page=1, size=20)
        save("itrs", itrs)

        print("[4] Punch Items 조회")
        punchitems = client.get_punchitems(page=1, size=20)
        save("punchitems", punchitems)

        print("\n완료. 결과는 output/ 폴더와 pims.log 를 확인하세요.")

        # ---------------- 저장 (POST) ----------------
        # 실제 필드명은 PIMS 스키마에 맞게 수정하세요.
        # new_tag = client.create_tag({
        #     "tagNo": "10-PT-1001",
        #     "description": "Pressure Transmitter",
        #     "subsystem": "SS-100",
        # })
        # print("생성된 Tag:", new_tag)

    except PimsError as exc:
        print(f"[PIMS 오류] {exc}")
        if exc.status_code is not None:
            print(f"  HTTP {exc.status_code}")
        if exc.body:
            print(f"  응답 본문: {exc.body[:500]}")
        print("  자세한 내용은 pims.log 를 확인하세요.")


if __name__ == "__main__":
    main()
