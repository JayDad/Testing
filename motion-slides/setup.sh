#!/usr/bin/env bash
# Motion Slides 환경 셋업 (Linux/macOS/WSL · Claude Code 클라우드 세션 공용)
#  - Python 패키지: python-pptx, PyYAML, Playwright
#  - Pretendard 웹폰트(OFL) → fonts/ (HTML·MP4 한글 렌더링용)
#  - Pretendard OTF → ~/.fonts (LibreOffice QA 렌더링용)
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install -q python-pptx pyyaml playwright 2>/dev/null \
  || python3 -m pip install -q --break-system-packages python-pptx pyyaml playwright

# Chromium: 사전 설치본(/opt/pw-browsers) 있으면 사용, 없으면 다운로드
if [ ! -e /opt/pw-browsers/chromium ]; then
  python3 -m playwright install chromium
fi

if [ ! -f fonts/PretendardVariable.woff2 ]; then
  tmp=$(mktemp -d)
  (cd "$tmp" && npm pack pretendard@1.3.9 >/dev/null 2>&1 && tar xzf pretendard-1.3.9.tgz)
  mkdir -p fonts ~/.fonts
  cp "$tmp/package/dist/web/variable/woff2/PretendardVariable.woff2" fonts/
  cp "$tmp"/package/dist/public/static/Pretendard-{Regular,Medium,SemiBold,Bold}.otf ~/.fonts/
  command -v fc-cache >/dev/null && fc-cache -f >/dev/null || true
  rm -rf "$tmp"
fi

command -v ffmpeg >/dev/null || echo "⚠ ffmpeg 미설치 — MP4 렌더링 불가 (apt/brew install ffmpeg)"
command -v soffice >/dev/null || echo "ℹ LibreOffice 미설치 — --qa 정지 장면 PNG 생략됨 (MP4는 정상)"
echo "✔ 셋업 완료 → python3 build.py specs/demo_production_methods.yaml --qa"
