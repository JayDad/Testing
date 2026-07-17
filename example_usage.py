"""PIMS 클라이언트 사용 예제.

실행 전에:
    1) cp .env.example .env  후 .env 에 인증 정보 입력
    2) pip install -r requirements.txt
    3) python example_usage.py
"""

from pims_client import PimsError, build_client_from_env


def main() -> None:
    # .env 를 읽어 환경변수 기반으로 클라이언트 생성
    client = build_client_from_env()

    try:
        # ---------------- 조회 (GET) ----------------
        # 필터/페이징 파라미터는 키워드 인자로 전달합니다.
        # (실제 파라미터명은 PIMS 문서 기준으로 맞추세요. 예: page, size, subsystem 등)
        tags = client.get_tags(page=1, size=20)
        print("Tags:", tags)

        subsystems = client.get_subsystems()
        print("SubSystems:", subsystems)

        itrs = client.get_itrs(page=1, size=20)   # ITR = tagevents
        print("ITRs:", itrs)

        punchitems = client.get_punchitems(page=1, size=20)
        print("Punch Items:", punchitems)

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


if __name__ == "__main__":
    main()
