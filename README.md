# PIMS REST API 클라이언트

PIMS(`gate-api.pimshosting.com`)의 CMS 리소스를 **조회(GET)/저장(POST)** 하는 Python 클라이언트입니다.

| 리소스 | 엔드포인트 | 편의 메서드 |
| --- | --- | --- |
| Tag | `/cms/tags` | `get_tags()`, `create_tag()` |
| SubSystem | `/cms/subsystems` | `get_subsystems()`, `create_subsystem()` |
| ITR (TagEvent) | `/cms/tagevents` | `get_itrs()`, `create_itr()` |
| Punch Item | `/cms/punchitems` | `get_punchitems()`, `create_punchitem()` |

## 인증 정보는 어디에 입력하나요?

**소스코드에 넣지 마세요.** `.env` 파일(또는 환경변수)에 넣으면 됩니다.

```bash
cp .env.example .env
# .env 를 열어 실제 값 입력
```

`.env` 는 `.gitignore` 에 등록되어 있어 git에 커밋되지 않습니다.
클라이언트는 요청할 때마다 `PimsClient._auth_headers()` **한 곳**에서
`.env` 값을 읽어 인증 헤더를 자동으로 붙입니다.

### 지원하는 인증 방식 (`PIMS_AUTH_SCHEME` 로 전환)

| 방식 | 설정할 값 | 실제로 붙는 헤더 |
| --- | --- | --- |
| `basic` (기본) | `PIMS_USERNAME`, `PIMS_PASSWORD` | `Authorization: Basic base64(id:pw)` |
| `bearer` | `PIMS_API_TOKEN` | `Authorization: Bearer <token>` |
| `apikey` | `PIMS_API_KEY`, `PIMS_API_KEY_HEADER` | `<header>: <key>` (기본 `x-api-key`) |

PIMS 발급처에서 안내받은 방식에 맞춰 `.env` 의 `PIMS_AUTH_SCHEME` 만 바꾸면 됩니다.
예를 들어 **Basic 인증**을 안내받았다면:

```dotenv
PIMS_AUTH_SCHEME=basic
PIMS_USERNAME=발급받은_아이디
PIMS_PASSWORD=발급받은_비밀번호
```

> ⚠️ `PIMS_API_TOKEN`/`PIMS_API_KEY` 에 예제의 placeholder 나 한글이 남아 있으면
> HTTP 헤더 인코딩 오류(`UnicodeEncodeError`)가 납니다. 사용하지 않는 방식의 값은
> 비워두거나 그대로 둬도 되지만, **실제 사용하는 방식**의 값은 반드시 채우세요.

## 설치 & 실행

```bash
pip install -r requirements.txt
cp .env.example .env      # 인증 정보 입력
python example_usage.py
```

## 사용 예

```python
from pims_client import build_client_from_env

client = build_client_from_env()   # .env 자동 로드

# 조회 (필터/페이징은 키워드 인자로)
tags = client.get_tags(page=1, size=20)
itrs = client.get_itrs()           # ITR = tagevents
punch = client.get_punchitems()

# 저장 (필드명은 PIMS 스키마에 맞게)
client.create_tag({
    "tagNo": "10-PT-1001",
    "description": "Pressure Transmitter",
    "subsystem": "SS-100",
})
```

코드로 직접 인증값을 넘기고 싶다면:

```python
from pims_client import PimsClient

client = PimsClient(
    base_url="https://gate-api.pimshosting.com",
    auth_scheme="apikey",
    api_key="발급받은_키",
    api_key_header="x-api-key",
)
```

## 참고

- 이 코드가 만들어진 환경에서는 네트워크 정책상 `gate-api.pimshosting.com` 접속이
  차단되어 있어, **실제 API 응답 스키마(필드명/파라미터명)는 검증하지 못했습니다.**
  조회 결과를 한번 출력해 보고 필드명을 실제 스키마에 맞춰 조정하세요.
