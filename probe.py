"""PIMS 엔드포인트 파라미터 탐색기.

예전 문서에 페이징/필터 파라미터가 안 나와 있어서, /cms/tags 같은 엔드포인트가
어떤 파라미터를 받아 "적게" 조회할 수 있는지 여러 관례를 자동으로 시도합니다.
정상 응답(HTTP 200)이 오는 조합을 찾으면, 그게 이 API가 쓰는 파라미터입니다.

사용:
    python probe.py               # tags 대상으로 탐색
    python probe.py subsystems    # 다른 리소스 대상
    python probe.py punchitems

주의: 서버가 파라미터를 무시하면 전체 조회를 시도하다 ~30초 후 500(DB 타임아웃)이
      납니다. 안 맞는 조합마다 30초씩 걸릴 수 있으니 몇 분 걸릴 수 있습니다.
      중간에 멈추려면 Ctrl+C.
"""

import sys
import time

from pims_client import PimsError, build_client_from_env, setup_logging

# 흔한 페이징 관례들 (작은 결과부터 요청해 DB 부하를 줄이는 게 목적)
PARAM_SETS = [
    {"size": 1},
    {"pageSize": 1},
    {"page": 1, "pageSize": 1},
    {"limit": 1},
    {"limit": 1, "offset": 0},
    {"$top": 1},
    {"$top": 1, "$skip": 0},
    {"top": 1},
    {"rows": 1},
    {"maxResults": 1},
]


def main() -> None:
    setup_logging()
    resource = sys.argv[1] if len(sys.argv) > 1 else "tags"
    client = build_client_from_env()

    print(f"'{resource}' 엔드포인트 파라미터 탐색 시작 (총 {len(PARAM_SETS)}개 조합)\n")
    winners = []
    for i, params in enumerate(PARAM_SETS, 1):
        start = time.monotonic()
        try:
            data = client.list(resource, **params)
            elapsed = time.monotonic() - start
            count = len(data) if isinstance(data, list) else "?"
            print(f"[{i}/{len(PARAM_SETS)}] ✅ 200  {params}  ({elapsed:.1f}s, 항목수={count})")
            print(f"           → 동작함! 응답 일부: {str(data)[:200]}")
            winners.append(params)
        except PimsError as exc:
            elapsed = time.monotonic() - start
            code = exc.status_code or "ERR"
            snippet = (exc.body or str(exc)).replace("\n", " ")[:100]
            print(f"[{i}/{len(PARAM_SETS)}] ❌ {code}  {params}  ({elapsed:.1f}s)  {snippet}")

    print("\n===== 결과 =====")
    if winners:
        print("동작하는 파라미터 조합:")
        for w in winners:
            print(f"  - {w}")
        print("\n이 파라미터를 example_usage.py / 코드의 조회 함수에 넣어 쓰면 됩니다.")
    else:
        print("정상 응답 조합을 못 찾았습니다. 다음을 의심하세요:")
        print("  1) 이 엔드포인트는 '필수 필터'(예: 프로젝트/설비 코드)가 있어야 할 수 있음")
        print("     → PIMS 발급처에 필수 파라미터를 문의하세요.")
        print("  2) 다른 엔드포인트로 시도: python probe.py subsystems")
        print("  3) 서버/DB 자체가 느린 상태일 수 있음")


if __name__ == "__main__":
    main()
