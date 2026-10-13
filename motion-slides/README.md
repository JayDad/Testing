# Motion Slides — YAML 1개로 유튜브 배경 모션(MP4)·모핑 PPTX 제작

## 엔진 2종 (spec에 `beats:` 있으면 비트 엔진 자동 선택)

| 엔진 | spec 키 | 산출물 | 용도 |
|---|---|---|---|
| **비트(Beat) 엔진 — 유튜브 트렌드형 (기본 권장)** | `beats:` | HTML(GSAP) · MP4 | 유튜브 배경·B-roll, 다크 그라디언트 + 키네틱 타이포 + 3D UI + 문서 하이라이트 |
| 장면(Scene) 엔진 — 보고용 | `scenes:` | 모핑 PPTX · HTML · MP4 | 사내 보고 장표 모핑, PowerPoint 재편집 필요 시 |

### 비트 유형 (`specs/trend_demo.yaml`)

| type | 연출 | 주요 키 |
|---|---|---|
| `kinetic` | 단어 단위 스탬프 등장, `*강조*` 단어 시안 + 밑줄 드로잉 | `eyebrow` `lines` `size` |
| `stat` | 숫자 카운트업 + 진행 바 | `value` `suffix` `label` `bar` `caption` |
| `ui_cards` | 글래스 카드 3D 비행 진입, 카메라 궤도 이동, 포커스 카드 강조 | `title` `cards[{label,desc}]` `focus` |
| `doc_highlight` | 문서 카드 등장 → 형광펜 스윕 → 해당 문장으로 카메라 줌 | `source` `title` `lines` `hl` |
| `before_after` | 보고용 장표(BEFORE) → 수직 와이프 → 키네틱(AFTER) | `before_title` `after_text` |
| `endcard` | 마스크 상승 제목 + 라인 드로잉 | `title` `sub` |

- 비트 간 전환: `transition: zoom`(기본, 줌 스루) · `slide` · `cut`
- `meta.safe_zone: right|left` → 발표자 PIP 자리 비움
- 배경 글로우·그리드는 전 구간 연속 이동(정지 화면 방지), 렌더링 20초 영상 기준 약 2분

---

## Executive Summary

- 장면(Scene) YAML 1개 작성 → **① 모핑 PPTX ② 애니메이션 HTML ③ MP4** 3종 동시 생성
- PPTX는 python-pptx 미지원 영역인 모핑 전환 XML을 직접 삽입, 개체명 `!!id`로 장면 간 매칭 강제 — PowerPoint 2019 / M365에서 바로 재생
- MP4는 HTML을 headless Chromium으로 프레임 단위 캡처 → FFmpeg 인코딩 (HyperFrames와 동일 원리, 외부 서비스·라이선스 비용 없음)
- 다크블루 테마 토큰·좌표계(13.333 × 7.5 inch, Pretendard) 그대로 적용, 제목·구분선·페이지번호 자동 생성

## 테스트 결과 (`output/demo_production_methods/`)

| 산출물 | 내용 | 결과 |
|---|---|---|
| `deck.pptx` | 4장, 2~4장 모핑 전환(1.2초) · 장면당 자동 넘김 3초 | 생성 확인, 모핑 XML·`!!` 개체명 삽입 확인 |
| `motion.mp4` | 1920×1080 · 30fps · 16.9초 | 507프레임 렌더링 약 65초 소요 |
| `motion.html` | 브라우저 반복 재생 미리보기, 폰트 내장 단독 파일 | 정상 |
| `qa/slide-*.png` | PPTX 정지 장면 | 넘침·겹침 없음 |
| `qa/contact_sheet.png` | MP4 1초 간격 프레임 | 모핑 중간 프레임 확인 |

- 미검증: Windows PowerPoint에서의 실제 모핑 재생·MP4 내보내기 품질 → 사내 PC 확인 필요 (Next Actions 1)

## 사용 경로 3가지

| 경로 | 방법 | 적합 용도 |
|---|---|---|
| A. Claude에게 요청 | Claude Code에서 `/motion-slides 주제·자료` → 장면 설계·빌드·QA·파일 전달 자동 진행 | 신규 제작 (권장) |
| B. 직접 수정·빌드 | spec YAML 문구·좌표 수정 → `python3 build.py specs/<이름>.yaml --qa` | 기존 장면 문구 교체·재사용 |
| C. 사내 PC 변환 | `build.py --only pptx` → PPTX를 `tools/export_mp4.bat`에 끌어다 놓기 | 사내 한정 자료 (외부 처리 없음) |

## 빠른 시작

```bash
bash motion-slides/setup.sh                               # 최초 1회 (패키지·폰트)
cd motion-slides
python3 build.py --new 주간브리핑                          # 템플릿 복사 → specs/주간브리핑.yaml
python3 build.py specs/주간브리핑.yaml --qa                 # PPTX + HTML + MP4 + QA 이미지
python3 build.py specs/주간브리핑.yaml --only pptx          # 모핑 PPTX만
```

## 장면 작성 규칙 (spec YAML)

```yaml
meta: {project_title: "Trion FPU · 주간", hold: 3.0, morph: 1.2, logo: null}
scenes:
  - title: "핵심 이슈"                      # 제목·부제 미기재 시 직전 장면 유지
    subtitle: "현황"
    elements:
      - {id: a, style: card, x: 0.60, y: 1.95, w: 3.84, h: 3.75, lines: [
          {t: "01", size: 32, bold: true, color: navy}, {t: "설명", size: 16}]}
  - remove: [msg]                           # 퇴장 개체
    elements:
      - {id: a, x: 4.15, w: 8.58, style: navycard}   # 같은 id → 위치·크기·색 모핑
```

- 단위: 좌표 inch, 글자 pt / 콘텐츠 영역 x 0.60~12.73, y 1.95~6.90
- 장면은 직전 장면 상속(변경 키만 기재), `remove` 퇴장, `reset: true` 초기화
- style 프리셋: `text` `card` `navycard` `highlight` `banner` `bar`
- 색 토큰: `navy` `text` `caption` `white` `highlight` `divider` (또는 HEX)
- 3·4·5열 카드, 칩+패널 등 자주 쓰는 좌표는 `specs/_template.yaml` 상단 주석 참고

## 파일 구성

| 파일 | 역할 |
|---|---|
| `motion_slides.py` | spec 해석 · 모핑 PPTX · HTML 애니메이션 · MP4 렌더링 엔진 |
| `build.py` | CLI (빌드·QA·템플릿 생성) |
| `specs/_template.yaml` | 신규 작성용 템플릿 (좌표 치트시트 포함) |
| `specs/demo_production_methods.yaml` | 테스트 장면 (제작 방식 5계열 → 권고 3경로) |
| `tools/export_mp4.ps1` · `.bat` | Windows PowerPoint 자동 MP4 내보내기 (COM `CreateVideo`) |
| `setup.sh` | 패키지·Chromium·Pretendard 설치 |
| `../.claude/skills/motion-slides/SKILL.md` | Claude Code 스킬 (경로 A) |

## 제약·리스크

- 보안: 경로 A·B의 MP4 렌더링은 Claude 실행 환경에서 처리 → 사내 한정 자료는 경로 C(PPTX만 생성 후 사내 PC 변환) 적용
- 모핑 매칭은 개체명 `!!id` 기준 → PowerPoint에서 개체명 변경 시 해당 개체 모핑 해제
- 문구가 바뀌는 개체는 교차 페이드 처리(PowerPoint 모핑도 동일), 숫자 카운트업·파티클 등 고급 효과 미지원
- 모핑 미지원 버전(2016 이하)은 페이드로 대체 재생
- LibreOffice QA 이미지는 한글·괄호 주변 간격이 넓게 보이나 PowerPoint에서는 정상 표시

## Next Actions

1. 사내 PC에서 `deck.pptx` 슬라이드 쇼(F5) 모핑 재생 확인 → `export_mp4.bat` MP4 품질 비교 (HTML 렌더 MP4 대비)
2. 실제 보고 주제 1건으로 경로 A 시험 (`/motion-slides` + 원자료 첨부)
3. 로고 파일 확정 시 `meta.logo` 지정, 영상 배경 전용은 `page_numbers: false` 적용
