"""PIMS 클라이언트 사용 예제 (Omega 365 기반 gate-api).

실행 전에:
    1) cp .env.example .env  후 .env 에 인증 정보 입력
    2) pip install -r requirements.txt
    3) python example_usage.py

이 API 핵심:
    - 조회 파라미터: maxRecords(개수), skip(offset), whereClause(SQL 필터)
    - 응답은 HAL 형식: {"_total": 전체건수, "_items": [...], "_links": {...}}
    - tags 는 10만건 이상이라 maxRecords 없이 조회하면 서버가 타임아웃(500)납니다.

결과를 보는 곳:
    - 터미널 화면
    - pims.log        : 요청/응답 로그
    - output/*.json   : 조회한 데이터
"""

import json
from pathlib import Path

from pims_client import PimsError, build_client_from_env, setup_logging

OUTPUT_DIR = Path("output")


def save(name: str, data) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장됨 → {path}")


def show(client, resource: str, response) -> None:
    """HAL 응답 요약 출력 + 첫 항목의 필드명 안내."""
    total = client.total(response)
    items = client.items(response)
    print(f"  전체 건수(_total) = {total}, 이번에 받은 항목 = {len(items)}개")
    if items:
        print(f"  필드 목록: {list(items[0].keys())}")


def main() -> None:
    setup_logging(logfile="pims.log")
    client = build_client_from_env()

    try:
        # ---------------- 조회 (GET) ----------------
        # 반드시 maxRecords 로 개수를 제한하세요. (편의 메서드는 기본 50)
        print("[1] Tags 조회 (maxRecords=5)")
        tags = client.get_tags(max_records=5)
        show(client, "tags", tags)
        save("tags", tags)

        print("[2] SubSystems 조회 (maxRecords=50)")
        subsystems = client.get_subsystems(max_records=50)
        show(client, "subsystems", subsystems)
        save("subsystems", subsystems)

        print("[3] ITR(tagevents) 조회 (maxRecords=50)")
        itrs = client.get_itrs(max_records=50)
        show(client, "tagevents", itrs)
        save("itrs", itrs)

        print("[4] Punch Items 조회 (maxRecords=50)")
        punchitems = client.get_punchitems(max_records=50)
        show(client, "punchitems", punchitems)
        save("punchitems", punchitems)

        # ---------------- 필터 조회 (whereClause) ----------------
        # output/tags.json 에서 실제 필드명을 확인한 뒤, 그 컬럼으로 필터하세요.
        # 예) 특정 Domain 만: (컬럼명은 실제 스키마에 맞게 수정)
        # filtered = client.get_tags(max_records=100, where="Domain='0202'")
        # show(client, "tags(filtered)", filtered)

        # ---------------- 전체 페이지 순회 ----------------
        # ⚠️ tags 는 10만건이라 전체 순회는 매우 오래 걸립니다. 반드시 where 로 좁히세요.
        # count = 0
        # for tag in client.iter_all("tags", page_size=1000, where="Domain='0202'"):
        #     count += 1
        # print(f"필터 조건에 해당하는 tag 총 {count}건")

        # ---------------- 저장 (POST) ----------------
        # 실제 필드명은 output/*.json 을 보고 맞추세요.
        # new_tag = client.create_tag({"TagNo": "10-PT-1001", "Description": "..."})
        # print("생성된 Tag:", new_tag)

        print("\n완료. output/ 폴더와 pims.log 를 확인하세요.")

    except PimsError as exc:
        print(f"[PIMS 오류] {exc}")
        if exc.status_code is not None:
            print(f"  HTTP {exc.status_code}")
        if exc.body:
            print(f"  응답 본문: {exc.body[:500]}")
        print("  자세한 내용은 pims.log 를 확인하세요.")


if __name__ == "__main__":
    main()
