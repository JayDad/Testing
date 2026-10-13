/* beats_runtime.js — 유튜브 배경용 '비트(Beat)' 모션 런타임
 * 트렌드 반영 원칙
 *  - 한 화면 한 메시지(카드당 8단어 내외), 텍스트가 주인공(키네틱 타이포)
 *  - 페이드 대신 공간 전환(줌 스루·슬라이드), 카메라는 멈추지 않고 미세 이동
 *  - 다크 그라디언트 배경 + 그리드·그레인 텍스처, 강조색은 핵심 단어에만
 * 모든 애니메이션은 하나의 GSAP 타임라인 → window.__seek(t)로 프레임 단위 결정론적 렌더링
 */
(function () {
  const D = window.__BEATS__;
  const stage = document.getElementById('stage');
  const cam = document.getElementById('cam');
  const tl = gsap.timeline({ paused: true });

  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const rich = s => esc(s).replace(/\*(.+?)\*/g, '<em>$1</em>');

  // 단어 분할 — *강조* 는 accent 클래스
  function words(host, text, mask) {
    const out = [];
    String(text).split(/(\*[^*]+\*)/).filter(Boolean).forEach(part => {
      const acc = part.startsWith('*') && part.endsWith('*');
      const t = acc ? part.slice(1, -1) : part;
      t.split(/(\s+)/).forEach(w => {
        if (!w) return;
        if (/^\s+$/.test(w)) { host.append(document.createTextNode(' ')); return; }
        const m = el('span', 'wm' + (mask ? ' mask' : ''));
        const s = el('span', 'w' + (acc ? ' acc' : ''), esc(w));
        m.append(s); host.append(m); out.push(s);
      });
    });
    return out;
  }

  // ---------------- 비트 유형 ----------------
  const B = {};

  // 1) 키네틱 타이포 — 단어가 스탬프처럼 꽂힘, 강조 단어 밑줄 드로잉
  B.kinetic = (b, root) => {
    const box = el('div', 'center col');
    root.append(box);
    let eb;
    if (b.eyebrow) { eb = el('div', 'eyebrow', esc(b.eyebrow)); box.append(eb); }
    const ws = [];
    (b.lines || []).forEach((ln, i) => {
      const d = el('div', 'kline'); d.style.fontSize = (b.size || 132) + 'px';
      box.append(d); ws.push(...words(d, ln, false));
    });
    const acc = ws.filter(w => w.classList.contains('acc'));
    return t => {
      if (eb) tl.fromTo(eb, { opacity: 0, y: 24, letterSpacing: '0.6em' }, { opacity: 1, y: 0, letterSpacing: '0.32em', duration: .6, ease: 'power3.out' }, t + .05);
      tl.fromTo(ws, { opacity: 0, scale: 1.55, y: 18, filter: 'blur(14px)' },
        { opacity: 1, scale: 1, y: 0, filter: 'blur(0px)', duration: .3, ease: 'back.out(1.8)', stagger: .11 }, t + .2);
      if (acc.length) tl.fromTo(acc, { backgroundSize: '0% 10px' }, { backgroundSize: '100% 10px', duration: .45, ease: 'power2.inOut', stagger: .1 }, t + .3 + ws.length * .11);
      tl.fromTo(box, { y: 10 }, { y: -14, duration: b.dur, ease: 'none' }, t);
    };
  };

  // 2) 빅 넘버 — 카운트업 + 진행 바
  B.stat = (b, root) => {
    const box = el('div', 'center col');
    const num = el('div', 'bignum');
    const v = el('span', 'val', fmt(b.from || 0, b.decimals));
    num.append(v);
    if (b.suffix) num.append(el('span', 'suf', esc(b.suffix)));
    const lab = el('div', 'stat-label'); const lw = words(lab, b.label || '', true);
    const bar = el('div', 'bar'); const fill = el('div', 'fill'); bar.append(fill);
    box.append(num, lab);
    if (b.bar != null) box.append(bar);
    let cap; if (b.caption) { cap = el('div', 'caption', esc(b.caption)); box.append(cap); }
    root.append(box);
    function fmt(x, d) { return Number(x).toLocaleString('ko-KR', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); }
    return t => {
      const o = { v: b.from || 0 };
      tl.fromTo(num, { opacity: 0, scale: .7, filter: 'blur(20px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: .5, ease: 'power3.out' }, t + .1);
      tl.fromTo(o, { v: b.from || 0 }, { v: b.value, duration: 1.3, ease: 'power2.out', onUpdate: () => { v.textContent = fmt(o.v, b.decimals); } }, t + .15);
      tl.fromTo(lw, { yPercent: 110 }, { yPercent: 0, duration: .5, ease: 'power3.out', stagger: .06 }, t + .7);
      if (b.bar != null) tl.fromTo(fill, { scaleX: 0 }, { scaleX: b.bar, duration: 1.2, ease: 'power2.inOut' }, t + .5);
      if (cap) tl.fromTo(cap, { opacity: 0 }, { opacity: 1, duration: .5 }, t + 1.2);
      tl.fromTo(box, { scale: 1 }, { scale: 1.05, duration: b.dur, ease: 'none' }, t);
    };
  };

  // 3) 3D UI 카드 — 글래스 카드 비행 진입 + 카메라 궤도 이동 + 포커스
  B.ui_cards = (b, root) => {
    const title = el('div', 'h-title'); const tw = words(title, b.title || '', true);
    const scene = el('div', 'scene3d'); const row = el('div', 'cards3d');
    const cards = (b.cards || []).map((c, i) => {
      const k = el('div', 'gcard');
      k.append(el('div', 'gnum', String(i + 1).padStart(2, '0')), el('div', 'glabel', rich(c.label)), el('div', 'gdesc', rich(c.desc || '')));
      row.append(k); return k;
    });
    scene.append(row); root.append(title, scene);
    return t => {
      tl.fromTo(tw, { yPercent: 110 }, { yPercent: 0, duration: .55, ease: 'power3.out', stagger: .07 }, t + .1);
      tl.fromTo(cards, { opacity: 0, z: -600, y: 80, rotateX: 25 }, { opacity: 1, z: 0, y: 0, rotateX: 0, duration: .8, ease: 'power3.out', stagger: .16 }, t + .35);
      tl.fromTo(row, { rotateY: -16, rotateX: 8 }, { rotateY: -4, rotateX: 4, duration: b.dur, ease: 'sine.inOut' }, t);
      if (b.focus != null && cards[b.focus]) {
        const others = cards.filter((_, i) => i !== b.focus);
        tl.to(others, { opacity: .28, filter: 'blur(3px)', duration: .5, ease: 'power2.out' }, t + b.dur * .55);
        tl.to(cards[b.focus], { scale: 1.08, z: 80, borderColor: 'rgba(124,224,255,.95)', boxShadow: '0 0 80px rgba(76,141,255,.55)', duration: .5, ease: 'power2.out' }, t + b.dur * .55);
      }
    };
  };

  // 4) 문서 하이라이트 — 형광펜 스윕 후 해당 문장으로 카메라 줌
  B.doc_highlight = (b, root) => {
    const wrap = el('div', 'center');
    const paper = el('div', 'paper');
    if (b.source) paper.append(el('div', 'p-src', esc(b.source)));
    paper.append(el('div', 'p-title', esc(b.title || '')));
    const lines = (b.lines || []).map((ln, i) => {
      const p = el('p', 'p-line'); const s = el('span', i === b.hl ? 'mark' : '', esc(ln)); p.append(s); paper.append(p); return p;
    });
    wrap.append(paper); root.append(wrap);
    return t => {
      tl.fromTo(paper, { opacity: 0, y: 120, rotate: -7 }, { opacity: 1, y: 0, rotate: -2, duration: .7, ease: 'power3.out' }, t + .05);
      tl.fromTo(lines, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: .4, ease: 'power2.out', stagger: .1 }, t + .4);
      const mk = paper.querySelector('.mark');
      if (mk) {
        tl.fromTo(mk, { backgroundSize: '0% 100%' }, { backgroundSize: '100% 100%', duration: .7, ease: 'power2.inOut' }, t + 1.1);
        const hlLine = lines[b.hl];
        tl.to(lines.filter(l => l !== hlLine), { opacity: .3, duration: .5 }, t + 1.7);
        tl.to(paper, { scale: 1.32, rotate: 0, transformOrigin: () => `50% ${((hlLine.offsetTop + hlLine.offsetHeight / 2) / paper.offsetHeight * 100).toFixed(1)}%`, duration: 1.1, ease: 'power2.inOut' }, t + 1.6);
      }
    };
  };

  // 5) 비포/애프터 — 수직 와이프
  B.before_after = (b, root) => {
    const before = el('div', 'ba before'); const after = el('div', 'ba after');
    before.append(el('div', 'ba-tag', esc(b.before_label || 'BEFORE')));
    const mock = el('div', 'mock');
    mock.append(el('div', 'mock-title', esc(b.before_title || '')));
    const mrow = el('div', 'mock-row');
    for (let i = 0; i < 3; i++) { const c = el('div', 'mock-card'); c.append(el('i'), el('i'), el('i')); mrow.append(c); }
    mock.append(mrow); before.append(mock);
    after.append(el('div', 'ba-tag acc', esc(b.after_label || 'AFTER')));
    const ac = el('div', 'center-abs'); const ak = el('div', 'kline'); ak.style.fontSize = (b.size || 140) + 'px';
    const aw = words(ak, b.after_text || '', false); ac.append(ak); after.append(ac);
    const line = el('div', 'ba-line');
    root.append(before, after, line);
    return t => {
      tl.fromTo(mock, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: .5, ease: 'power2.out' }, t + .1);
      tl.fromTo(after, { clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0% 0 0)', duration: 1.0, ease: 'power3.inOut' }, t + 1.1);
      tl.fromTo(line, { left: '0%', opacity: 1 }, { left: '100%', duration: 1.0, ease: 'power3.inOut' }, t + 1.1);
      tl.to(line, { opacity: 0, duration: .2 }, t + 2.1);
      tl.fromTo(aw, { opacity: 0, scale: 1.5, filter: 'blur(12px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: .3, ease: 'back.out(1.8)', stagger: .1 }, t + 1.6);
    };
  };

  // 6) 엔드카드 — 제목 마스크 상승 + 라인 드로잉
  B.endcard = (b, root) => {
    const box = el('div', 'center col');
    const ti = el('div', 'kline'); ti.style.fontSize = (b.size || 150) + 'px';
    const tw = words(ti, b.title || '', true);
    const ln = el('div', 'endline');
    const sub = el('div', 'sub', rich(b.sub || ''));
    box.append(ti, ln, sub); root.append(box);
    return t => {
      tl.fromTo(tw, { yPercent: 115 }, { yPercent: 0, duration: .7, ease: 'expo.out', stagger: .09 }, t + .1);
      tl.fromTo(ln, { scaleX: 0 }, { scaleX: 1, duration: .8, ease: 'power3.inOut' }, t + .6);
      tl.fromTo(sub, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: .6, ease: 'power2.out' }, t + 1.0);
      tl.fromTo(box, { scale: 1 }, { scale: 1.04, duration: b.dur, ease: 'none' }, t);
    };
  };

  // ---------------- 타임라인 조립 ----------------
  const OVER = D.overlap;
  let T = 0;
  D.beats.forEach((b, i) => {
    const root = el('div', 'beat');
    if (D.safe_zone) root.classList.add('safe-' + D.safe_zone);
    cam.append(root);
    const anim = (B[b.type] || B.kinetic)(b, root);
    gsap.set(root, { opacity: 0 });
    const tr = b.transition || 'zoom';
    // 진입
    if (i === 0) tl.fromTo(root, { opacity: 0 }, { opacity: 1, duration: .4 }, T);
    else if (tr === 'slide') tl.fromTo(root, { opacity: 0, xPercent: 12, filter: 'blur(10px)' }, { opacity: 1, xPercent: 0, filter: 'blur(0px)', duration: .6, ease: 'power3.out' }, T);
    else if (tr === 'cut') tl.set(root, { opacity: 1 }, T);
    else tl.fromTo(root, { opacity: 0, scale: .9, filter: 'blur(12px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: .6, ease: 'power3.out' }, T);
    anim(T);
    const end = T + b.dur;
    // 퇴장 (마지막 비트는 유지)
    const nx = D.beats[i + 1];
    if (nx) {
      const ntr = nx.transition || 'zoom';
      if (ntr === 'slide') tl.to(root, { opacity: 0, xPercent: -12, filter: 'blur(10px)', duration: .5, ease: 'power2.in' }, end - .5);
      else if (ntr === 'cut') tl.set(root, { opacity: 0 }, end);
      else tl.to(root, { opacity: 0, scale: 1.2, filter: 'blur(18px)', duration: .5, ease: 'power2.in' }, end - .5);
      T = end - (ntr === 'cut' ? 0 : OVER);
    } else T = end;
  });
  // 배경 글로우 — 전체 구간 연속 이동(정지 화면 방지)
  tl.fromTo('#glow1', { xPercent: -10, yPercent: -5 }, { xPercent: 15, yPercent: 10, duration: T, ease: 'none' }, 0);
  tl.fromTo('#glow2', { xPercent: 10, yPercent: 5 }, { xPercent: -15, yPercent: -10, duration: T, ease: 'none' }, 0);
  tl.fromTo('#grid', { backgroundPosition: '0px 0px' }, { backgroundPosition: `0px ${Math.round(T * 12)}px`, duration: T, ease: 'none' }, 0);

  const DUR = T + (D.tail || 0.3);
  window.__duration = DUR;
  window.__seek = t => { tl.seek(Math.min(t, tl.duration()), false); };

  if (location.search.includes('capture')) { document.body.classList.add('capture'); window.__seek(0); }
  else {
    const fit = () => { const k = Math.min(innerWidth / 1920, innerHeight / 1080); stage.style.transform = `scale(${k})`; };
    addEventListener('resize', fit); fit();
    let t0 = null;
    const loop = ts => { if (t0 === null) t0 = ts; window.__seek(((ts - t0) / 1000) % DUR); requestAnimationFrame(loop); };
    document.fonts.ready.then(() => requestAnimationFrame(loop));
  }
})();
