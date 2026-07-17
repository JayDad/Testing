"""PIMS REST API 클라이언트.

PIMS(gate-api.pimshosting.com)의 CMS 리소스를 조회/저장하기 위한 얇은 래퍼입니다.

지원 리소스:
    - tags        : Tag 목록/저장
    - subsystems  : SubSystem 목록/저장
    - tagevents   : ITR (Inspection Test Record) 목록/저장
    - punchitems  : Punch Item 목록/저장

인증(Authentication)
--------------------
인증 정보는 소스코드에 절대 하드코딩하지 마세요.
`.env` 파일이나 환경변수에 넣으면 이 클라이언트가 자동으로 읽어서
요청 헤더에 붙입니다. (`.env.example` 참고)

세 가지 방식을 환경변수 하나(PIMS_AUTH_SCHEME)로 전환할 수 있습니다:
    1) bearer  : Authorization: Bearer <PIMS_API_TOKEN>
    2) apikey  : <PIMS_API_KEY_HEADER>: <PIMS_API_KEY>   (기본 헤더명 x-api-key)
    3) basic   : Authorization: Basic base64(PIMS_USERNAME:PIMS_PASSWORD)

PIMS 발급처에서 정확한 방식(헤더명/토큰 종류)을 확인한 뒤 .env 값만 맞추면 됩니다.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any, Optional

import requests

# 이 모듈에서 사용하는 로거. setup_logging() 을 호출하면 콘솔+파일로 출력됩니다.
logger = logging.getLogger("pims")


def setup_logging(logfile: str | os.PathLike[str] = "pims.log", level: int = logging.INFO) -> None:
    """콘솔과 파일 양쪽으로 로그를 남기도록 설정합니다.

    호출 후에는 모든 요청/응답이 `logfile` 에 기록됩니다.
    """
    fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)

    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setFormatter(fmt)

    root = logging.getLogger("pims")
    root.setLevel(level)
    root.handlers.clear()          # 중복 등록 방지
    root.addHandler(console)
    root.addHandler(file_handler)


# ---------------------------------------------------------------------------
# .env 로더 (python-dotenv 미설치 환경에서도 동작하도록 최소 구현)
# ---------------------------------------------------------------------------
def load_dotenv(path: str | os.PathLike[str] = ".env") -> None:
    """`.env` 파일을 읽어 아직 설정되지 않은 환경변수를 채웁니다.

    이미 존재하는 환경변수는 덮어쓰지 않습니다(실제 환경변수가 우선).
    """
    env_path = Path(path)
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class PimsError(RuntimeError):
    """PIMS API 호출 실패 시 발생하는 예외."""

    def __init__(self, message: str, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class PimsClient:
    """PIMS CMS REST API 클라이언트."""

    # 문서에 나온 리소스 경로 (base_url 뒤에 붙습니다)
    RESOURCES = {
        "tags": "cms/tags",
        "subsystems": "cms/subsystems",
        "tagevents": "cms/tagevents",   # ITR
        "punchitems": "cms/punchitems",
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        auth_scheme: Optional[str] = None,
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_header: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> None:
        # 값이 명시되지 않으면 환경변수에서 읽습니다.
        self.base_url = (base_url or os.getenv("PIMS_BASE_URL", "https://gate-api.pimshosting.com")).rstrip("/")
        self.auth_scheme = (auth_scheme or os.getenv("PIMS_AUTH_SCHEME", "bearer")).lower()
        self.token = token or os.getenv("PIMS_API_TOKEN")
        self.api_key = api_key or os.getenv("PIMS_API_KEY")
        self.api_key_header = api_key_header or os.getenv("PIMS_API_KEY_HEADER", "x-api-key")
        self.username = username or os.getenv("PIMS_USERNAME")
        self.password = password or os.getenv("PIMS_PASSWORD")
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    # ------------------------------------------------------------------
    # 인증 헤더 — 인증이 적용되는 "단 한 곳"
    # ------------------------------------------------------------------
    @staticmethod
    def _check_header_value(value: str, env_name: str) -> str:
        """헤더에 들어갈 값이 유효한지 검증합니다.

        HTTP 헤더 값은 latin-1 로 인코딩 가능해야 합니다. 한글 등 비ASCII 문자가
        들어있으면(예: .env 의 placeholder 를 실제 값으로 안 바꾼 경우) urllib3 가
        `UnicodeEncodeError` 를 내는데, 그 전에 여기서 명확한 메시지로 잡아줍니다.
        """
        try:
            value.encode("latin-1")
        except UnicodeEncodeError:
            raise PimsError(
                f"{env_name} 값에 한글 등 비ASCII 문자가 들어있습니다. "
                f".env 의 {env_name} 에 예제 placeholder 대신 발급받은 실제 값을 "
                f"넣었는지 확인하세요. (현재 값 앞부분: {value[:12]!r}...)"
            )
        return value

    def _auth_headers(self) -> dict[str, str]:
        """설정된 인증 방식에 맞는 헤더를 만듭니다."""
        if self.auth_scheme == "bearer":
            if not self.token:
                raise PimsError("PIMS_API_TOKEN 이 설정되지 않았습니다 (bearer 방식).")
            self._check_header_value(self.token, "PIMS_API_TOKEN")
            return {"Authorization": f"Bearer {self.token}"}

        if self.auth_scheme == "apikey":
            if not self.api_key:
                raise PimsError("PIMS_API_KEY 가 설정되지 않았습니다 (apikey 방식).")
            self._check_header_value(self.api_key, "PIMS_API_KEY")
            return {self.api_key_header: self.api_key}

        if self.auth_scheme == "basic":
            if not (self.username and self.password):
                raise PimsError("PIMS_USERNAME / PIMS_PASSWORD 가 설정되지 않았습니다 (basic 방식).")
            raw = f"{self.username}:{self.password}".encode("utf-8")
            encoded = base64.b64encode(raw).decode("ascii")
            return {"Authorization": f"Basic {encoded}"}

        if self.auth_scheme in ("none", ""):
            return {}

        raise PimsError(f"알 수 없는 PIMS_AUTH_SCHEME: {self.auth_scheme!r} (bearer/apikey/basic/none 중 하나)")

    # ------------------------------------------------------------------
    # 저수준 요청
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info("→ %s %s params=%s", method, url, params or {})
        try:
            headers = self._auth_headers()
        except PimsError as exc:
            logger.error("✗ 인증 설정 오류: %s", exc)
            raise
        try:
            resp = self.session.request(
                method,
                url,
                params=params,
                json=json,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:  # 네트워크/연결 오류
            logger.error("✗ %s %s 요청 실패: %s", method, url, exc)
            raise PimsError(f"요청 실패: {method} {url} ({exc})") from exc

        logger.info("← %s %s HTTP %s (%d bytes)", method, url, resp.status_code, len(resp.content))
        if not resp.ok:
            logger.error("✗ HTTP %s 응답 본문: %s", resp.status_code, resp.text[:500])
            raise PimsError(
                f"{method} {url} -> HTTP {resp.status_code}",
                status_code=resp.status_code,
                body=resp.text,
            )

        if not resp.content:
            return None
        ctype = resp.headers.get("Content-Type", "")
        if "application/json" in ctype:
            return resp.json()
        return resp.text

    # ------------------------------------------------------------------
    # 범용 조회/저장
    # ------------------------------------------------------------------
    def _resolve(self, resource: str) -> str:
        if resource in self.RESOURCES:
            return self.RESOURCES[resource]
        # 이미 경로(cms/xxx)를 직접 넘긴 경우도 허용
        return resource

    def list(self, resource: str, **params: Any) -> Any:
        """리소스 목록 조회 (GET). 필터/페이징은 키워드 인자로 전달."""
        return self._request("GET", self._resolve(resource), params=params or None)

    def get(self, resource: str, item_id: str | int) -> Any:
        """단건 조회 (GET /resource/{id})."""
        return self._request("GET", f"{self._resolve(resource)}/{item_id}")

    def create(self, resource: str, payload: dict[str, Any] | list[Any]) -> Any:
        """저장 (POST). payload 는 dict 또는 list."""
        return self._request("POST", self._resolve(resource), json=payload)

    def update(self, resource: str, item_id: str | int, payload: dict[str, Any]) -> Any:
        """수정 (PUT /resource/{id})."""
        return self._request("PUT", f"{self._resolve(resource)}/{item_id}", json=payload)

    # ------------------------------------------------------------------
    # 리소스별 편의 메서드
    # ------------------------------------------------------------------
    # Tags
    def get_tags(self, **params: Any) -> Any:
        return self.list("tags", **params)

    def create_tag(self, payload: dict[str, Any]) -> Any:
        return self.create("tags", payload)

    # SubSystems
    def get_subsystems(self, **params: Any) -> Any:
        return self.list("subsystems", **params)

    def create_subsystem(self, payload: dict[str, Any]) -> Any:
        return self.create("subsystems", payload)

    # ITR (TagEvents)
    def get_itrs(self, **params: Any) -> Any:
        return self.list("tagevents", **params)

    def create_itr(self, payload: dict[str, Any]) -> Any:
        return self.create("tagevents", payload)

    # Punch Items
    def get_punchitems(self, **params: Any) -> Any:
        return self.list("punchitems", **params)

    def create_punchitem(self, payload: dict[str, Any]) -> Any:
        return self.create("punchitems", payload)


def build_client_from_env(dotenv_path: str = ".env") -> PimsClient:
    """.env 를 로드한 뒤 환경변수 기반으로 클라이언트를 만듭니다."""
    load_dotenv(dotenv_path)
    return PimsClient()


# ---------------------------------------------------------------------------
# CLI — `python pims_client.py <리소스>` 로 바로 조회할 수 있습니다.
#   예) python pims_client.py tags -p page=1 -p size=20
# ---------------------------------------------------------------------------
def _main(argv: Optional[list[str]] = None) -> int:
    import argparse
    import json as _json
    import sys

    parser = argparse.ArgumentParser(description="PIMS REST API 조회 CLI")
    parser.add_argument(
        "resource",
        nargs="?",
        choices=["tags", "subsystems", "tagevents", "itr", "punchitems"],
        help="조회할 리소스 (itr = tagevents)",
    )
    parser.add_argument(
        "-p", "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="쿼리 파라미터 (여러 번 사용 가능). 예: -p page=1 -p size=20",
    )
    args = parser.parse_args(argv)

    if not args.resource:
        parser.print_help()
        print("\n예) python pims_client.py tags -p page=1 -p size=20")
        return 0

    setup_logging()
    client = build_client_from_env()

    params: dict[str, Any] = {}
    for kv in args.param:
        key, _, value = kv.partition("=")
        params[key] = value

    resource = "tagevents" if args.resource == "itr" else args.resource
    try:
        data = client.list(resource, **params)
        print(_json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except PimsError as exc:
        print(f"[PIMS 오류] {exc}", file=sys.stderr)
        if exc.body:
            print(exc.body[:500], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
