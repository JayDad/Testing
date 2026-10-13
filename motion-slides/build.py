#!/usr/bin/env python3
"""
사용법
  python build.py specs/demo_production_methods.yaml            # PPTX + HTML + MP4 전부
  python build.py specs/xxx.yaml --only pptx                    # 모핑 PPTX만 (사내 자료)
  python build.py specs/xxx.yaml --only html,mp4                # 영상 경로만
  python build.py specs/xxx.yaml --qa                           # 정지 장면 PNG + 영상 콘택트시트
  python build.py --new 주간브리핑                               # 템플릿 복사 → specs/주간브리핑.yaml

산출물: output/<spec 이름>/  (deck.pptx · motion.html · motion.mp4 · qa/)
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motion_slides as ms  # noqa: E402


def qa_pptx(pptx, qa_dir):
    """LibreOffice로 PPTX → PDF → 장면별 PNG (모핑은 미재생, 정지 레이아웃 점검용)"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("  [QA] LibreOffice 없음 → PPTX 정지 점검 생략")
        return
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(qa_dir),
                    str(pptx)], check=True, capture_output=True)
    pdf = qa_dir / (pptx.stem + ".pdf")
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-r", "60", "-png", str(pdf), str(qa_dir / "slide")], check=True)
        pdf.unlink()
    print(f"  [QA] 정지 장면 → {qa_dir}")


def qa_mp4(mp4, qa_dir, duration):
    """영상 1초 간격 프레임 콘택트시트 — 모핑 중간 프레임 확인용"""
    n = max(1, int(duration))
    cols = 4
    rows = (n + cols - 1) // cols
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf",
                    f"fps=1,scale=480:-1,tile={cols}x{rows}:padding=6:color=white",
                    "-frames:v", "1", str(qa_dir / "contact_sheet.png")], check=True)
    print(f"  [QA] 콘택트시트 → {qa_dir / 'contact_sheet.png'}")


def build_beats(spec, out, a, qa_dir):
    """비트 엔진(유튜브 배경 트렌드형) — HTML + MP4"""
    import beats as bt
    meta, beats = bt.load(spec)
    print(f"▶ {spec.name}: 비트 {len(beats)}개 (트렌드형 · GSAP) → {out}")
    h = bt.build_html(meta, beats, out / "motion.html")
    print(f"  ✔ HTML 미리보기  {h}")
    t0 = time.time()
    fps = a.fps or int(meta["fps"])
    m, n = ms.render_mp4(h, out / "motion.mp4", None, fps=fps)
    print(f"  ✔ MP4  {m}  ({n}프레임 · {n / fps:.1f}초, {time.time() - t0:.0f}초 소요)")
    if a.qa:
        qa_mp4(Path(m), qa_dir, n / fps)


def main():
    ap = argparse.ArgumentParser(description="Scene YAML → 모핑 PPTX / 애니메이션 HTML / MP4")
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--new", metavar="NAME", help="템플릿으로 새 spec 생성")
    ap.add_argument("--only", default="pptx,html,mp4", help="pptx,html,mp4 중 선택(쉼표)")
    ap.add_argument("--out", default=None, help="출력 폴더 (기본 output/<spec 이름>)")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--qa", action="store_true", help="정지 장면 PNG·콘택트시트 생성")
    a = ap.parse_args()

    here = Path(__file__).resolve().parent
    if a.new:
        dst = here / "specs" / f"{a.new}.yaml"
        if dst.exists():
            sys.exit(f"이미 존재: {dst}")
        shutil.copy(here / "specs" / "_template.yaml", dst)
        print(f"✔ 생성: {dst}\n  편집 후 → python build.py {dst.relative_to(here)} --qa")
        return
    if not a.spec:
        ap.error("spec 경로 또는 --new 필요")

    spec = Path(a.spec)
    targets = {t.strip() for t in a.only.split(",")}
    out = Path(a.out) if a.out else Path(__file__).resolve().parent / "output" / spec.stem
    out.mkdir(parents=True, exist_ok=True)
    qa_dir = out / "qa"
    if a.qa:
        qa_dir.mkdir(exist_ok=True)

    import yaml
    if "beats" in (yaml.safe_load(spec.read_text(encoding="utf-8")) or {}):
        return build_beats(spec, out, a, qa_dir)

    meta, scenes = ms.load_spec(spec)
    fps = a.fps or int(meta["fps"])
    print(f"▶ {spec.name}: 장면 {len(scenes)}개 → {out}")

    if "pptx" in targets:
        p = ms.build_pptx(meta, scenes, out / "deck.pptx")
        print(f"  ✔ 모핑 PPTX  {p}")
        if a.qa:
            qa_pptx(Path(p), qa_dir)

    if targets & {"html", "mp4"}:
        h, dur = ms.build_html(meta, scenes, out / "motion.html")
        print(f"  ✔ HTML 미리보기  {h}  ({dur:.1f}초, 브라우저로 열면 반복 재생)")
        if "mp4" in targets:
            if not ms.FONT_FILE.exists():
                print("  ⚠ Pretendard 웹폰트 없음 → setup.sh 먼저 실행 권장 (대체 글꼴로 렌더링됨)")
            t0 = time.time()
            m, n = ms.render_mp4(h, out / "motion.mp4", dur, fps=fps)
            print(f"  ✔ MP4  {m}  ({n}프레임, {time.time() - t0:.0f}초 소요)")
            if a.qa:
                qa_mp4(Path(m), qa_dir, dur)


if __name__ == "__main__":
    main()
