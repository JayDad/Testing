---
name: motion-slides
description: 유튜브 배경 모션 영상(키네틱 타이포·3D UI·문서 하이라이트 비트) 및 다크블루 모핑 PPTX 제작 — 주제·자료를 받아 YAML spec 작성 후 HTML·MP4(·PPTX) 빌드. "모션 슬라이드", "애니메이션 슬라이드", "유튜브 배경", "B-roll", "모핑 장표", "/motion-slides" 요청 시 사용
---

# Motion Slides — 유튜브 배경 모션(비트) · 모핑 PPTX

## 엔진 선택 (먼저 판단)
- 유튜브 배경·B-roll·SNS 영상 → **비트 엔진** (`beats:` spec, 예시 `motion-slides/specs/trend_demo.yaml`) — 기본값
- 사내 보고 장표에 모핑만 필요, PowerPoint 재편집 필요 → 장면 엔진 (`scenes:` spec)
- 비트 작성 원칙: 비트당 1메시지·8단어 이하·3~4초, 강조는 `*핵심 단어*`만, 비트 유형을 연속 반복하지 않음(시각 변화 유지)
- 비트 유형: kinetic · stat · ui_cards · doc_highlight · before_after · endcard (키는 `motion-slides/README.md` 표 참고)
- 새 비트 유형 필요 시 `motion-slides/beats_runtime.js`의 `B.<type>`에 GSAP 함수 추가

엔진: `motion-slides/` (repo 루트 기준). 상세 문법은 `motion-slides/specs/_template.yaml` 상단 주석, 완성 예시는 `motion-slides/specs/demo_production_methods.yaml` 참고

## 절차

1. **입력 확인** (질문은 한 번에 묶어서, 이미 답이 있으면 생략)
   - 주제·원자료(문서·기존 PPT·HTML 브리핑), 장면 수(기본 3~5), 산출 경로
   - 보안 등급: 사내 한정 자료 → `--only pptx` (모핑 PPTX만, 사용자 PC에서 MP4 변환) / 공개 가능 → 전체 빌드
   - 로고 파일 여부(없으면 우측 상단 비움), 상단 프로젝트명 문구
2. **환경 점검**: `motion-slides/fonts/PretendardVariable.woff2` 없으면 `bash motion-slides/setup.sh` 실행
3. **장면 설계 → spec 작성**: `python3 motion-slides/build.py --new <이름>` 후 편집
   - 장면 = 하나의 메시지, 장면 간 같은 id 개체가 이동·확대·색 변경되도록 설계 (모핑의 핵심)
   - 패턴: ① 개관(N개 카드) → ② 하나 확대 + 나머지 칩 축소 → ③ 초점 이동 → ④ 결론 재배치 + 배너
   - 문체: 명사형 종결(~함, ~계획, ~추진), 마침표 없음
   - 색: navy · text · caption · white · highlight 토큰만 사용 (다크블루 테마 규칙)
   - 콘텐츠 영역 x 0.60~12.73, y 1.95~6.90 준수, 카드 본문 14pt 이상
4. **빌드**: `python3 motion-slides/build.py motion-slides/specs/<이름>.yaml --qa` (MP4 15초 기준 약 1분)
5. **QA (필수)**: `output/<이름>/qa/slide-*.png`(정지 장면)와 `qa/contact_sheet.png`(1초 간격 프레임)를 Read로 확인
   - 텍스트 넘침·겹침·여백 과다 → spec 수정 후 재빌드
   - LibreOffice 렌더링은 한글·괄호 주변 간격이 넓게 보이나 PowerPoint에서는 정상
6. **전달**: deck.pptx, motion.mp4를 SendUserFile로 전송, 아래 안내 첨부
   - PowerPoint에서 모핑 확인: 슬라이드 쇼(F5)
   - 사내 PC에서 MP4: `motion-slides/tools/export_mp4.bat`에 PPTX 끌어다 놓기
   - motion.html: 브라우저로 열면 반복 재생(폰트 내장, 단독 파일)

## 주의

- 모핑 매칭은 개체명 `!!id` 기준 — PowerPoint에서 개체명 수정 시 모핑 해제
- 텍스트 문구가 바뀌는 개체는 교차 페이드, 문구가 같으면 크기·색만 보간
- spec 수정 이력은 git으로 관리 (장면 재현성 확보)
