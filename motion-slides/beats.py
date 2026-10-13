"""
beats.py — 유튜브 배경용 '비트(Beat)' 모션 → HTML(GSAP) → MP4

spec 예시 (specs/trend_demo.yaml 참고)
  meta: {theme: dark, safe_zone: none, overlap: 0.3}
  beats:
    - {type: kinetic, dur: 3.2, eyebrow: "...", lines: ["...", "*강조* 단어"]}
    - {type: stat, dur: 3.0, value: 8, suffix: "단어", label: "...", bar: 0.8}
    - {type: ui_cards, dur: 4.0, title: "...", cards: [{label, desc}], focus: 0}
    - {type: doc_highlight, dur: 4.0, title: "...", lines: [...], hl: 1}
    - {type: before_after, dur: 3.4, before_title: "...", after_text: "..."}
    - {type: endcard, dur: 3.0, title: "...", sub: "..."}
  transition: zoom(기본) | slide | cut  — 해당 비트로 들어올 때의 전환
"""

import base64
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
FONT_FILE = ROOT / "fonts" / "PretendardVariable.woff2"
GSAP_FILE = ROOT / "vendor" / "gsap.min.js"
RUNTIME_FILE = ROOT / "beats_runtime.js"

# 다크 테마 — 브랜드 네이비(#012060)를 배경 글로우로, 밝은 블루·시안을 강조색으로
THEMES = {
    "dark": dict(bg="#030817", glow1="rgba(1,32,96,.95)", glow2="rgba(27,77,255,.35)",
                 text="#FFFFFF", muted="#8FA3C7", accent="#4C8DFF", accent2="#7CE0FF",
                 marker="rgba(255,214,64,.85)"),
}

CSS = r"""
html,body{margin:0;background:#000;height:100%}
body{display:flex;align-items:center;justify-content:center;overflow:hidden}
#stage{position:relative;width:1920px;height:1080px;overflow:hidden;background:var(--bg);
  font-family:'Pretendard','Malgun Gothic','Apple SD Gothic Neo',sans-serif;color:var(--text);
  -webkit-font-smoothing:antialiased;font-feature-settings:'tnum';letter-spacing:-0.02em}
body.capture{display:block;background:var(--bg)}
body.capture #stage{transform:none!important}
.glow{position:absolute;border-radius:50%}
#glow1{width:1300px;height:1000px;left:-250px;top:-300px;background:radial-gradient(circle,var(--glow1),transparent 70%)}
#glow2{width:1100px;height:900px;right:-300px;bottom:-350px;background:radial-gradient(circle,var(--glow2),transparent 70%)}
#grid{position:absolute;inset:-100px;opacity:.07;
  background-image:linear-gradient(var(--muted) 1px,transparent 1px),linear-gradient(90deg,var(--muted) 1px,transparent 1px);
  background-size:80px 80px;-webkit-mask-image:radial-gradient(ellipse at center,#000 30%,transparent 75%)}
#grain{position:absolute;inset:0;opacity:.05;pointer-events:none;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}
#vignette{position:absolute;inset:0;background:radial-gradient(ellipse at center,transparent 55%,rgba(0,0,0,.55));pointer-events:none}
#cam{position:absolute;inset:0;perspective:1800px}
.beat{position:absolute;inset:0;will-change:transform,opacity,filter}
.beat.safe-right{right:34%}.beat.safe-left{left:34%}
.center{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.col{flex-direction:column;text-align:center}
.eyebrow{font-size:28px;font-weight:600;letter-spacing:.32em;text-transform:uppercase;color:var(--accent2);margin-bottom:36px}
.kline{font-weight:820;line-height:1.12;letter-spacing:-0.035em}
.wm{display:inline-block;vertical-align:top}
.wm.mask{overflow:hidden;padding-bottom:.08em;margin-bottom:-.08em}
.w{display:inline-block;transform-origin:50% 60%}
.w.acc,em{font-style:normal;color:var(--accent2);text-shadow:0 0 40px rgba(124,224,255,.45);
  background:linear-gradient(var(--accent),var(--accent)) no-repeat 0 96%/0% 10px}
em{background-size:0 0}
.bignum{font-size:300px;font-weight:880;line-height:1;letter-spacing:-0.05em;
  background:linear-gradient(180deg,#fff 30%,var(--accent2));-webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 0 60px rgba(76,141,255,.35))}
.bignum .suf{font-size:110px;margin-left:18px;font-weight:700}
.stat-label{font-size:52px;font-weight:700;margin-top:18px}
.bar{width:760px;height:10px;border-radius:5px;background:rgba(255,255,255,.1);margin-top:44px;overflow:hidden}
.bar .fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));transform-origin:0 50%;box-shadow:0 0 24px var(--accent)}
.caption{font-size:30px;color:var(--muted);margin-top:28px;letter-spacing:.02em}
.h-title{position:absolute;left:150px;top:120px;font-size:64px;font-weight:800}
.scene3d{position:absolute;inset:230px 60px 60px;display:flex;align-items:center;justify-content:center;perspective:1600px}
.cards3d{display:flex;gap:44px;transform-style:preserve-3d}
.gcard{width:540px;height:520px;box-sizing:border-box;padding:52px 48px;border-radius:28px;
  background:linear-gradient(160deg,rgba(255,255,255,.12),rgba(255,255,255,.03));
  border:1.5px solid rgba(124,224,255,.32);box-shadow:0 0 40px rgba(76,141,255,.18),inset 0 1px 0 rgba(255,255,255,.25);
  transform-style:preserve-3d}
.gnum{font-size:30px;font-weight:700;color:var(--accent2);letter-spacing:.1em}
.glabel{font-size:64px;font-weight:800;margin:120px 0 22px;line-height:1.1}
.gdesc{font-size:34px;color:var(--muted);line-height:1.4}
.paper{width:1240px;box-sizing:border-box;padding:70px 84px;border-radius:14px;background:#F6F7F9;color:#141A26;
  box-shadow:0 40px 120px rgba(0,0,0,.6)}
.p-src{font-size:22px;color:#6B7A93;letter-spacing:.08em;text-transform:uppercase;margin-bottom:14px}
.p-title{font-size:52px;font-weight:800;margin-bottom:34px;letter-spacing:-0.03em}
.p-line{font-size:36px;line-height:1.5;margin:0 0 14px;font-weight:500}
.p-line .mark{background:linear-gradient(var(--marker),var(--marker)) no-repeat 0 0/0% 100%;padding:2px 6px;margin:0 -6px;font-weight:700}
.ba{position:absolute;inset:0}
.before{background:#E9EBEF}
.after{background:var(--bg);background-image:radial-gradient(circle at 30% 30%,var(--glow1),transparent 60%)}
.ba-tag{position:absolute;left:80px;top:70px;font-size:32px;font-weight:700;letter-spacing:.24em;color:#5A6478}
.ba-tag.acc{color:var(--accent2);text-shadow:none;background:none}
.mock{position:absolute;left:200px;right:200px;top:220px;bottom:200px}
.mock-title{font-size:56px;font-weight:800;color:#012060;border-bottom:3px solid #012060;padding-bottom:20px;margin-bottom:44px}
.mock-row{display:flex;gap:36px}
.mock-card{flex:1;height:330px;background:#fff;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,.08);padding:36px;box-sizing:border-box}
.mock-card i{display:block;height:18px;border-radius:9px;background:#D5DAE3;margin-bottom:22px}
.mock-card i:first-child{width:40%;height:40px;background:#012060;opacity:.8}
.mock-card i:last-child{width:70%}
.center-abs{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-wrap:wrap;align-content:center;text-align:center;padding:0 160px}
.ba-line{position:absolute;top:0;bottom:0;width:6px;margin-left:-3px;background:var(--accent2);box-shadow:0 0 40px var(--accent2)}
.endline{width:520px;height:6px;border-radius:3px;margin:46px 0 34px;background:linear-gradient(90deg,var(--accent),var(--accent2));box-shadow:0 0 30px var(--accent)}
.sub{font-size:40px;color:var(--muted);font-weight:500}
"""


def load(path):
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    meta = dict(theme="dark", safe_zone=None, overlap=0.3, fps=30, title="Motion Beats")
    meta.update(spec.get("meta") or {})
    beats = []
    for b in spec["beats"]:
        b = dict(b)
        b["dur"] = float(b.get("dur", 3.0))
        beats.append(b)
    return meta, beats


def build_html(meta, beats, out_path):
    th = THEMES[meta["theme"]]
    vars_css = ":root{" + "".join(f"--{k}:{v};" for k, v in th.items()) + "}"
    font_css = ""
    if FONT_FILE.exists():
        b64 = base64.b64encode(FONT_FILE.read_bytes()).decode()
        font_css = ("@font-face{font-family:'Pretendard';font-weight:45 920;"
                    f"src:url(data:font/woff2;base64,{b64}) format('woff2-variations');}}")
    data = dict(beats=beats, overlap=meta["overlap"], safe_zone=meta.get("safe_zone"))
    html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{meta['title']}</title>
<style>{font_css}{vars_css}{CSS}</style></head>
<body><div id="stage">
<div class="glow" id="glow1"></div><div class="glow" id="glow2"></div><div id="grid"></div>
<div id="cam"></div><div id="vignette"></div><div id="grain"></div>
</div>
<script>{GSAP_FILE.read_text(encoding="utf-8")}</script>
<script>window.__BEATS__={json.dumps(data, ensure_ascii=False)};</script>
<script>{RUNTIME_FILE.read_text(encoding="utf-8")}</script>
</body></html>"""
    Path(out_path).write_text(html, encoding="utf-8")
    return out_path
