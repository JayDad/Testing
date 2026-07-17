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

## 조회 파라미터 (중요)

이 API는 Omega 365 기반이라 페이징/필터 파라미터가 정해져 있습니다:

| 파라미터 | 의미 | 예 |
| --- | --- | --- |
| `maxRecords` | 가져올 최대 개수 | `maxRecords=50` |
| `skip` | 건너뛸 개수(offset) | `skip=100` |
| `whereClause` | SQL 필터 | `whereClause=Domain='0202'` |

> ⚠️ **`maxRecords`를 반드시 지정하세요.** 예를 들어 tags 는 10만건(`_total`=101,553)이라,
> 개수 제한 없이 조회하면 서버가 전체를 스캔하다 **500(DB 타임아웃)** 이 납니다.
> (`pageSize`/`limit`/`$top` 같은 다른 이름은 이 API가 무시합니다.)

응답은 **HAL 형식**입니다:
```json
{ "_total": 101553, "_items": [ { ... }, ... ], "_links": { "next": { "href": "..." } } }
```
실제 데이터는 `_items`, 전체 건수는 `_total`. `PimsClient.items(resp)` / `PimsClient.total(resp)` 로 꺼냅니다.

## 사용 예

```python
from pims_client import build_client_from_env

client = build_client_from_env()   # .env 자동 로드

# 조회 — 반드시 개수 제한
resp = client.get_tags(max_records=50)
print(client.total(resp))          # 전체 건수
for tag in client.items(resp):     # 실제 데이터 목록
    print(tag)

# 필터 조회 (whereClause) — 컬럼명은 output/tags.json 에서 확인 후 사용
resp = client.get_tags(max_records=100, where="Domain='0202'")

# 전체 페이지 순회 (제너레이터) — 반드시 where 로 좁혀서!
for tag in client.iter_all("tags", page_size=1000, where="Domain='0202'"):
    ...

itrs = client.get_itrs(max_records=50)      # ITR = tagevents
punch = client.get_punchitems(max_records=50)

# 단건 조회 (단수형 경로 /cms/tag/{id})
one = client.get_tag("0202_C&E")

# 저장 (필드명은 output/*.json 을 보고 맞추세요)
client.create_tag({"TagNo": "10-PT-1001", "Description": "Pressure Transmitter"})
```

CLI 로도 바로 조회할 수 있습니다:
```bash
python pims_client.py tags -n 10                       # 10건 조회
python pims_client.py tags -n 50 --where "Domain='0202'"
python pims_client.py tags --total                     # 전체 건수만
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

## 파라미터 탐색기 (probe.py)

문서에 없는 파라미터를 찾을 때 씁니다. 실제로 이걸로 `maxRecords` 를 찾아냈습니다.
```bash
python probe.py tags          # 여러 페이징 관례를 시도해 동작하는 것을 찾음
python probe.py subsystems
```

## 참고

- 이 시스템은 **Omega 365** 플랫폼 기반 PIMS 입니다.
- 조회 파라미터(`maxRecords`/`skip`/`whereClause`)와 HAL 응답 형식은 **실제 호출로 검증**됐습니다.
- 각 리소스의 **필드명**(예: tags 의 `Domain`, `TagNo` 등)은 `output/*.json` 을 열어 확인한 뒤
  `whereClause` 필터나 저장 payload 에 사용하세요.
- **성능**: tags 는 10만건 이상이고 요청 1건당 ~30초가 걸립니다. 전체를 받기보다
  `whereClause` 로 범위를 좁혀 쓰는 것을 강력히 권장합니다.
- **사내망**: 외부(`gate-api.pimshosting.com`) 접속이 막히면 `.env` 에 `PIMS_PROXY` 를 설정하세요.
