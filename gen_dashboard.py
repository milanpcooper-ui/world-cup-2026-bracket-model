# -*- coding: utf-8 -*-
"""Generate the standalone interactive dashboard HTML from results.json.

One template, written to the standalone download (World_Cup_2026_Predictor.html) and
the Pages root (index.html). It ships a light/dark toggle (no more
per-file colour scheme), team flags, confidence rings, a mobile-first
round-by-round bracket, a colourful "Today's movement" card built on the
matchup-change tracking, and a "Follow your team" view that works for any of
the 48 sides.
"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "results.json")))

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>World Cup 2026 — Predictive Bracket</title>
<meta name="description" content="Who's most likely to play in each World Cup 2026 knockout game, mapped to host city & date — for ticket & travel planning. Updates every 3 hours during the tournament.">
<meta name="theme-color" content="#1f4fd6">
<meta property="og:type" content="website">
<meta property="og:title" content="World Cup 2026 — Predictive Bracket">
<meta property="og:description" content="Who's most likely to play in each knockout game, mapped to host city & date. Market-anchored Monte Carlo, updates every 3 hours.">
<meta property="og:url" content="__OGURL__">
<!-- og:image is absolute when WC_SITE_URL is set at build time; link unfurls (iMessage/Slack/X) need the absolute form. -->
<meta property="og:image" content="__OGIMAGE__">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/css/flag-icons.min.css">
<script>(function(){try{var t=localStorage.getItem('wc-theme');if(!t)t=(window.matchMedia&&matchMedia('(prefers-color-scheme:dark)').matches)?'dark':'light';document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','light');}})();</script>
<style>
/* ===== Matchday design tokens — warm paper, one ink-blue, a hot vermilion
   signal, a cool→hot round arc. Raw color literals live ONLY in these two
   blocks; everything else routes through a var(). ===== */
:root{
 --bg:#f4f1ea;--panel:#fffdf8;--panel2:#ece6d9;--ink:#1a1814;--mut:#6b6354;
 --bd:#e2dccd;--bd2:#cabda6;--accent:#1f4fd6;--accent2:#4a74ec;
 --good:#1f7a4d;--bad:#c0392f;--gold:#9a6313;
 /* ink = text-on-light variants tuned to clear WCAG AA; flip to bright in dark mode */
 --good-ink:#1b6b43;--bad-ink:#a93226;--gold-ink:#7e5012;--teal-ink:#1f4fd6;--blue-ink:#1d4ed8;
 /* round arc — cool→hot, lands on the signal at the Final */
 --r32:#2f6bd6;--r16:#5a59d8;--qf:#8b46cf;--sf:#c83e95;--fin:#ee5a37;
 --track:#e2dccd;--navon:#e7eefc;--navonink:#1a3c97;
 --grad:linear-gradient(118deg,#1f4fd6 0%,#1c3fae 100%);
 --shadow:0 1px 1px rgba(26,22,14,.04);
 --overlay:rgba(26,24,20,.46);--engrow:#e7eefc;
 /* hot signal — live/now + the Final */
 --signal:#ee5a37;--signal-ink:#c0432a;--signal-pulse:rgba(238,90,55,.5);
 /* on-gradient (the blue header field) + on-saturated-fill text */
 --hero-ink:#fbfaf5;--hero-mut:rgba(255,255,255,.9);--on-fill:#ffffff;
 --grad-fill:rgba(255,255,255,.16);--grad-fill-2:rgba(255,255,255,.24);
 --grad-fill-3:rgba(255,255,255,.32);--grad-bd:rgba(255,255,255,.30);
 /* movement-chip fills: palette hues fixed dark-enough for white text in BOTH themes (AA ≥5:1) */
 --chip-flip:#c0432a;--chip-res:#1f7a4d;--chip-title:#9a6313;--chip-route:#1f4fd6;--chip-look:#8b46cf;
 --flag-edge:rgba(0,0,0,.12);
 /* crisp editorial radii */
 --r-sm:4px;--r-md:7px;--r-lg:9px;--r-xl:10px;--r-2xl:12px;--r-3xl:16px;--r-pill:999px;
 /* type roles — Archivo display · IBM Plex Sans body · IBM Plex Mono numbers */
 --font-display:"Archivo","Arial Narrow",system-ui,sans-serif;
 --font-sans:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 --font-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
 --font-emoji:"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif;
}
html[data-theme="dark"]{
 --bg:#14120d;--panel:#1d1a13;--panel2:#26221a;--ink:#f3efe4;--mut:#a39b8a;
 --bd:#2f2a20;--bd2:#483f2c;--accent:#6f9bff;--accent2:#9bbcff;
 --good:#3fbf7f;--bad:#ff6b5e;--gold:#dca64a;
 --good-ink:#3fbf7f;--bad-ink:#ff8a80;--gold-ink:#dca64a;--teal-ink:#6f9bff;--blue-ink:#7cb0ff;
 --r32:#4f7ee6;--r16:#7b78ec;--qf:#a874e0;--sf:#e06bb0;--fin:#ff7a52;
 --track:#2f2a20;--navon:#1c2742;--navonink:#9bbcff;
 --grad:linear-gradient(118deg,#21407f 0%,#18305f 100%);
 --shadow:0 1px 2px rgba(0,0,0,.4);
 --overlay:rgba(6,5,2,.62);--engrow:#16213b;
 --signal:#ff7a52;--signal-ink:#ff8a66;--signal-pulse:rgba(255,122,82,.5);
 --hero-ink:#f3efe4;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);transition:background .25s,color .25s;
 font:15px/1.5 var(--font-sans);
 -webkit-text-size-adjust:100%}
a{color:var(--accent);cursor:pointer;text-decoration:none}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
/* every NUMBER goes mono + tabular so columns align; names/labels stay sans */
td:not(:first-child),th:not(:first-child),.pc,.ring .pc,.stat .v,.dchip{
 font-family:var(--font-mono);font-variant-numeric:tabular-nums lining-nums;font-feature-settings:"tnum" 1,"lnum" 1}
.tcell,.prob .nm,.tm .nm,.stat .l,.step .c{font-family:var(--font-sans)}
/* big headlines in Archivo display; small eyebrow labels in tracked mono */
.card h3,.box h3,.gtitle,.chhead .t{font-family:var(--font-display);font-weight:700;letter-spacing:-.01em}
.colhead,.step .r{font-family:var(--font-mono);letter-spacing:.12em}
.updatebar{display:flex;align-items:center;gap:12px;justify-content:center;
 flex-wrap:wrap;background:var(--grad);color:var(--hero-ink);padding:9px 14px;font-size:13.5px;font-weight:600}
.updatebar[hidden]{display:none}
.updatebar button{background:var(--grad-fill-2);border:1px solid var(--grad-bd);color:var(--hero-ink);
 border-radius:var(--r-md);padding:5px 13px;font-weight:700;cursor:pointer;font-size:13px}
.updatebar button:hover{background:var(--grad-fill-3)}
.updatebar button.x{padding:4px 9px;background:transparent;border:none;font-size:17px;line-height:1}
.wrap{max-width:1340px;margin:0 auto;padding:0 14px 96px}
.fl{font-family:var(--font-emoji);font-style:normal}
/* SVG flags (flag-icons): a hairline + tiny radius keep edges crisp */
.fl.fi{border-radius:2px;box-shadow:0 0 0 .5px var(--flag-edge);vertical-align:-.1em}

header{background:var(--grad);color:var(--hero-ink);border-radius:0 0 var(--r-3xl) var(--r-3xl);margin:0 -14px 14px;
 padding:18px 18px 16px;box-shadow:var(--shadow)}
.htop{display:flex;align-items:center;gap:10px}
h1{font-family:var(--font-display);font-size:clamp(18px,4.2vw,25px);margin:0;letter-spacing:-.01em;font-weight:800;flex:1;min-width:0}
.iconbtn{background:var(--grad-fill);border:1px solid var(--grad-bd);color:var(--hero-ink);
 border-radius:var(--r-md);padding:7px 11px;cursor:pointer;font-size:15px;line-height:1}
.iconbtn:hover{background:var(--grad-fill-3)}
.pills{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}
.pill{display:inline-flex;align-items:center;gap:5px;background:var(--grad-fill);
 border:1px solid var(--grad-bd);border-radius:var(--r-pill);padding:3px 11px;font-size:12px;color:var(--hero-ink)}
.sub{color:var(--hero-mut);font-size:13px;margin-top:9px;max-width:780px}
.follow{display:flex;align-items:center;gap:8px;margin-top:11px;flex-wrap:wrap}
.follow label{font-size:12.5px;color:var(--hero-mut)}
select#followsel{background:var(--grad-fill);color:var(--hero-ink);border:1px solid var(--grad-bd);
 border-radius:var(--r-md);padding:6px 9px;font-size:13.5px;font-weight:600;max-width:230px}
select#followsel option{color:var(--ink)}

nav{display:flex;gap:7px;overflow-x:auto;padding:2px 0 2px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
nav::-webkit-scrollbar{display:none}
nav button{background:var(--panel);color:var(--mut);border:1px solid var(--bd);padding:9px 15px;
 border-radius:var(--r-md);cursor:pointer;font-size:14px;font-weight:600;white-space:nowrap;flex:none}
nav button.on{background:var(--navon);color:var(--navonink);border-color:transparent}
section{display:none;margin-top:14px}
section.on{display:block}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:var(--r-2xl);padding:15px;box-shadow:var(--shadow)}
.muted{color:var(--mut)}

/* movement / what-changed card */
.changes{background:var(--panel);border:1px solid var(--bd);border-radius:var(--r-2xl);padding:0;margin-bottom:14px;
 overflow:hidden;box-shadow:var(--shadow)}
.chhead{background:var(--panel2);
 padding:12px 15px;display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.chhead .t{font-weight:800;font-size:15.5px}
.chhead .since{color:var(--mut);font-size:12px;font-weight:500}
.chtoggle{margin-left:auto;flex:none;background:transparent;border:1px solid var(--bd);color:var(--mut);
 border-radius:var(--r-md);width:28px;height:28px;cursor:pointer;font-size:12px;line-height:1;
 display:inline-flex;align-items:center;justify-content:center;transition:transform .18s ease,background .18s,color .18s}
.chtoggle:hover{background:var(--panel2);color:var(--ink)}
.changes.collapsed .chtoggle{transform:rotate(-90deg)}
.changes.collapsed .chbody{display:none}
.chbody{padding:6px 15px 13px}
.crow{padding:9px 0;border-top:1px solid var(--bd);display:flex;gap:11px;align-items:flex-start}
.crow:first-child{border-top:none}
.ctag{flex:none;font-size:11px;font-weight:700;letter-spacing:.3px;text-transform:uppercase;
 padding:4px 9px;border-radius:var(--r-sm);color:var(--on-fill);white-space:nowrap}
/* movement taxonomy — retoned to the round/status palette (design Badge); --on-fill clears AA */
.ctag.flip{background:var(--chip-flip)}.ctag.res{background:var(--chip-res)}
.ctag.title{background:var(--chip-title)}.ctag.route{background:var(--chip-route)}.ctag.look{background:var(--chip-look)}
.cbody{flex:1;min-width:0}
.mvrow{display:flex;flex-wrap:wrap;align-items:baseline;gap:5px 9px;padding:3px 0}
.mvrow .where{color:var(--mut);font-size:12.5px;display:inline-flex;gap:9px;flex-wrap:wrap}
.arrow{color:var(--mut)}.up{color:var(--good);font-weight:700}.down{color:var(--bad);font-weight:700}
.headline{font-weight:600}
.ctx{color:var(--mut);font-size:13px;line-height:1.55}
.mvitem{padding:9px 0;border-top:1px dashed var(--bd)}
.mvitem:first-child{border-top:none;padding-top:1px}
.why{font-size:12.5px;line-height:1.5;margin:5px 0 0;color:var(--mut)}
.why b{color:var(--ink);font-weight:700}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}
.dchip{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:600;
 border-radius:var(--r-pill);padding:3px 9px;border:1px solid var(--bd);background:var(--panel2);color:var(--mut)}
.dchip.up{color:var(--good-ink)}.dchip.down{color:var(--bad-ink)}.dchip.res{color:var(--ink)}
.dchip.reach{border-style:dashed;background:transparent;font-weight:500;font-style:italic;opacity:.85}
.dchip .fl{font-size:13px}

/* bracket */
.roundnav{display:flex;gap:7px;overflow-x:auto;padding:2px 0 10px;scrollbar-width:none}
.roundnav::-webkit-scrollbar{display:none}
.rbtn{flex:none;border:1px solid var(--bd);background:var(--panel);color:var(--mut);border-radius:var(--r-pill);
 padding:7px 14px;font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:7px}
.rbtn .dot{width:9px;height:9px;border-radius:3px}
.rbtn.on{color:var(--ink);border-color:var(--bd2);background:var(--panel2)}
/* (date/bracket order toggle removed — Bracket tab is fixed to date order) */
.legend{display:flex;gap:13px;flex-wrap:wrap;align-items:center;margin:2px 0 12px;font-size:12.5px;color:var(--mut)}
.bracket{display:flex;flex-direction:column;gap:12px}
.col{display:none;flex-direction:column;gap:11px}
.col.show{display:flex}
.colhead{font-size:12px;letter-spacing:.5px;text-transform:uppercase;color:var(--mut);font-weight:800;
 display:flex;align-items:center;gap:8px;padding:2px 2px 0}
.colhead .dot{width:10px;height:10px;border-radius:3px}
.m{background:var(--panel);border:1px solid var(--bd);border-left:6px solid var(--r32);border-radius:var(--r-xl);
 padding:11px 12px;cursor:pointer;transition:transform .1s,box-shadow .12s,border-color .12s;box-shadow:var(--shadow)}
.m:hover{transform:translateY(-2px);border-color:var(--bd2)}
.m.r16{border-left-color:var(--r16)}.m.qf{border-left-color:var(--qf)}
.m.sf{border-left-color:var(--sf)}.m.fin{border-left-color:var(--fin)}
.m.follow{box-shadow:0 0 0 2px var(--accent) inset,var(--shadow)}
.m .mh{display:flex;justify-content:space-between;gap:7px;font-size:11.5px;color:var(--mut);margin-bottom:7px}
.m .mh .where{display:inline-flex;align-items:center;gap:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.m .mh .when{flex:none}
.mrow{display:flex;align-items:center;justify-content:space-between;gap:9px}
.teams{display:flex;flex-direction:column;gap:5px;min-width:0;flex:1}
.tm{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:700;min-width:0}
.tm .fl{font-size:18px;flex:none}
.tm .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vsbar{display:flex;align-items:center;gap:8px;color:var(--mut);font-size:11px;font-weight:600}
.vsbar::before,.vsbar::after{content:"";height:1px;background:var(--bd);flex:1}
.ring{flex:none;text-align:center}
.ring .pc{font-size:12px;font-weight:800;margin-top:-2px}
.ring .lb{font-size:9.5px;color:var(--mut);letter-spacing:.3px}
.followtag{display:inline-block;font-size:10px;font-weight:800;color:var(--on-fill);background:var(--chip-route);
 border-radius:var(--r-sm);padding:2px 7px;margin-top:7px}

/* bracket tree (mirrored, connected) */
.bt-legend{font-size:12.5px;margin:2px 0 12px;max-width:820px}
.bt-scroll{overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--bd);border-radius:var(--r-2xl);background:var(--panel);box-shadow:var(--shadow);padding:6px}
.bt-sizer{position:relative;margin:0 auto}
.bt-canvas{position:relative;transform-origin:top left}
.bt-svg{position:absolute;inset:0;pointer-events:none;z-index:1}
.bt-box{position:absolute;background:var(--panel);border:1px solid var(--bd);border-radius:var(--r-xl);overflow:hidden;cursor:pointer;box-shadow:var(--shadow);z-index:2;transition:box-shadow .18s,border-color .18s}
.bt-box:hover{border-color:var(--bd2)}
.bt-box.foc{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent) inset,var(--shadow);z-index:4}
.bt-row{display:flex;align-items:center;gap:6px;padding:0 8px;overflow:hidden}
.bt-row.div{border-bottom:1px solid var(--bd)}
.bt-row.lose{opacity:.72}
.bt-row .fl{font-size:13px;flex:none}
.bt-nm{font-size:11.5px;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
.bt-row.win .bt-nm{font-weight:700;color:var(--ink)}
.bt-row.lose .bt-nm{font-weight:500;color:var(--mut)}
.bt-row.foc .bt-nm{font-weight:700;color:var(--accent)}
.bt-tk{flex:none;width:5px;height:5px;border-radius:50%}
.bt-star{color:var(--accent);font-size:10px;flex:none}
.bt-collabel{position:absolute;display:flex;align-items:center;justify-content:center;gap:6px}
.bt-collabel .dot{width:7px;height:7px;border-radius:2px;flex:none}
.bt-collabel .lb{font:600 10px/1 var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--mut);white-space:nowrap}
.bt-champ{position:absolute;text-align:center;z-index:5}
.bt-champ .cap{font:600 9.5px/1 var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
.bt-champ .row{display:flex;gap:7px;justify-content:center;align-items:center;margin-top:5px}
.bt-champ .row .nm{font:900 19px/1 var(--font-display);letter-spacing:-.02em;text-transform:uppercase;color:var(--ink)}
.bt-champ .pc{font:500 11px/1 var(--font-mono);color:var(--signal-ink);margin-top:4px;font-variant-numeric:tabular-nums}

/* stats + steps (your team) */
.statrow{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.stat{background:var(--panel2);border:1px solid var(--bd);border-radius:var(--r-lg);padding:11px 14px;min-width:104px;flex:1}
.stat .v{font-size:21px;font-weight:800}.stat .l{font-size:11.5px;color:var(--mut);margin-top:1px}
.path{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:11px;margin-top:13px}
.step{background:var(--panel2);border:1px solid var(--bd);border-radius:var(--r-lg);padding:12px}
.step .r{font-size:10.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.5px;font-weight:700}
.step .c{font-size:16px;font-weight:800;margin:4px 0}
.step .d{font-size:12px;color:var(--mut)}
.step .op{font-size:12.5px;margin-top:6px;display:flex;align-items:center;gap:6px}
.step .pp{font-size:12px;color:var(--teal-ink);font-weight:700;margin-top:5px}

/* tables */
.tabletools{display:flex;gap:10px;align-items:center;margin-bottom:11px;flex-wrap:wrap}
.search{background:var(--panel);border:1px solid var(--bd2);border-radius:var(--r-md);color:var(--ink);padding:9px 12px;width:200px;font-size:14px}
.tblwrap{background:var(--panel);border:1px solid var(--bd);border-radius:var(--r-2xl);padding:6px;overflow:auto;box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--bd);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:700;cursor:pointer;position:sticky;top:0;background:var(--panel);z-index:1}
tbody tr:hover td{background:var(--panel2)}
tr.foc td{background:var(--engrow)}
.tcell{display:inline-flex;align-items:center;gap:8px}.tcell .fl{font-size:17px}

/* groups */
.ggrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(320px,100%),1fr));gap:13px}
.gtitle{font-weight:800;margin-bottom:7px;font-size:14px}
.gscroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.gtbl td,.gtbl th{padding:6px 8px;font-size:12.5px}
.gtbl td:first-child,.gtbl th:first-child{white-space:normal}
@media(max-width:380px){.gtbl td,.gtbl th{padding:5px 5px;font-size:11.5px}}
.q1{color:var(--good-ink);font-weight:700}.q2{color:var(--blue-ink);font-weight:700}.q3{color:var(--gold-ink);font-weight:700}

/* modal */
.modal{position:fixed;inset:0;background:var(--overlay);display:none;align-items:flex-end;justify-content:center;z-index:50}
.modal.on{display:flex}
.box{background:var(--panel);border:1px solid var(--bd2);border-radius:var(--r-3xl) var(--r-3xl) 0 0;max-width:540px;width:100%;
 padding:20px;max-height:88vh;overflow:auto;box-shadow:var(--shadow)}
.box h3{margin:0 0 2px;font-size:18px}
.close{float:right;cursor:pointer;color:var(--mut);font-size:24px;line-height:1;background:none;border:none;
 padding:4px 8px;margin:-6px -8px 0 0;min-width:40px;min-height:40px;border-radius:var(--r-md)}
.close:hover{background:var(--panel2)}
.prob{display:flex;align-items:center;gap:9px;margin:6px 0}
.prob .nm{width:150px;display:inline-flex;align-items:center;gap:7px}.prob .nm .fl{font-size:17px}
.prob .track{flex:1;background:var(--track);border-radius:var(--r-pill);height:11px;overflow:hidden}
.prob .fill{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:var(--r-pill)}
.prob .pc{width:48px;color:var(--mut);font-size:12.5px;text-align:right}
.foot{color:var(--mut);font-size:12.5px;margin-top:28px;border-top:1px solid var(--bd);padding-top:14px}
ul.asm{padding-left:18px}ul.asm li{margin:6px 0}

@media(min-width:920px){
 .wrap{padding:0 18px 96px}
 header{margin:0 -18px 16px}
 .bracket{flex-direction:row;overflow-x:auto;gap:14px;padding-bottom:8px;align-items:flex-start}
 .col{display:flex!important;min-width:246px;flex:1}
 .colhead{justify-content:center}
 .roundnav{display:none}
 .modal{align-items:center;padding:18px}
 .box{border-radius:var(--r-3xl)}
}
/* teams table — Polymarket source sub-label on a column header */
.thsrc{display:block;font-size:10px;font-weight:600;color:var(--signal-ink);letter-spacing:.02em;margin-top:1px}
</style></head>
<body>
<div class="updatebar" id="updatebar" hidden role="status">
 <span class="msg">🔔 A newer bracket is available — refresh to see the latest.</span>
 <button onclick="doRefresh()">Refresh</button>
 <button class="x" aria-label="Dismiss" onclick="dismissUpdate()">×</button>
</div>
<div class="wrap">

<header>
 <div class="htop">
  <h1><span class="fl">🏆</span> World Cup 2026 — Predictive Bracket</h1>
  <button class="iconbtn" id="themebtn" aria-label="Toggle dark mode">🌙</button>
 </div>
 <div class="pills">
  <span class="pill" id="genpill"></span>
  <span class="pill" id="simpill"></span>
 </div>
 <div class="sub">Who's most likely to play in each knockout game — mapped to host city &amp; date, for ticket &amp; travel planning. <span style="white-space:nowrap">Market-anchored Monte Carlo</span>, updated every 3 hours.</div>
 <div class="follow">
  <label for="followsel">⭐ Follow a team</label>
  <select id="followsel"></select>
 </div>
</header>

<nav>
 <button data-t="bracket" class="on">Bracket</button>
 <button data-t="brackettree">🗂 Bracket tree</button>
 <button data-t="yourteam">⭐ Your team</button>
 <button data-t="teams">Teams</button>
 <button data-t="groups">Groups</button>
 <button data-t="method">Method</button>
</nav>

<section id="bracket" class="on">
 <div id="changes" class="changes"></div>
 <div class="roundnav" id="roundnav"></div>
 <div class="legend">
  <span class="muted">Tap any match for full odds · the ring shows the chance of that exact matchup · ⭐ = your team's projected box</span>
 </div>
 <div class="bracket" id="brk"></div>
 <div class="card" style="margin-top:12px"><b>🥉 Third-place match</b> <span class="muted" id="tpline"></span></div>
</section>

<section id="brackettree">
 <div class="bt-legend muted">The projected knockout tree — the most-likely matchup in each box, connected through to the Final. ⭐ marks your team's path; tap a box to follow its projected winner.</div>
 <div class="bt-scroll" id="btScroll"><div class="bt-sizer" id="btSizer"><div class="bt-canvas" id="btCanvas"></div></div></div>
</section>

<section id="yourteam"><div id="yt"></div></section>

<section id="teams">
 <div class="tabletools">
  <input class="search" id="tsearch" placeholder="🔎 filter team…">
  <span class="muted">Champion = <b>Polymarket</b> title odds, de-vigged · refreshed every 3h · tap a column to sort · tap a team for match-by-match odds</span>
 </div>
 <div class="tblwrap"><table id="ttbl"></table></div>
</section>

<section id="groups"><div class="ggrid" id="ggrid"></div></section>

<section id="method">
 <div class="card">
  <h3 style="margin-top:0">How this works</h3>
  <ul class="asm" id="asm"></ul>
  <h3>Calibration vs the betting market — title odds</h3>
  <div class="muted" style="margin-bottom:6px">Title probabilities — model output vs market. A close match means the engine reproduces the market at the top.</div>
  <div style="overflow:auto"><table id="caltbl"></table></div>
  <h3 id="mcalhd">Calibration vs the betting market — per-game lines</h3>
  <div class="muted" style="margin-bottom:6px">Scheduled-but-unplayed group games with a betting line are priced directly off the market's 1X2 odds. The model column should match the market by construction.</div>
  <div style="overflow:auto"><table id="mcaltbl"></table></div>
  <h3>Sources</h3>
  <div class="muted">Groups, fixtures, venues &amp; results: Fox Sports, CBS Sports. Knockout structure &amp; Annex C third-place allocation: FIFA regulations. Elo ratings: worldfootballrankings.com / eloratings.net. Title odds: Polymarket (de-vigged), refreshed every 3 hours.</div>
 </div>
</section>

<div class="foot">Predictions, not guarantees — early in the group stage the bracket is highly uncertain and shifts with every result. Rebuilt nightly. Not affiliated with FIFA.</div>
</div>

<div class="modal" id="modal" role="dialog" aria-modal="true" aria-label="Details" aria-hidden="true"><div class="box" id="mbox"></div></div>

<script>
const DATA = __DATA__;
const FLAG = {"Mexico":"🇲🇽","South Africa":"🇿🇦","South Korea":"🇰🇷","Czechia":"🇨🇿","Canada":"🇨🇦","Bosnia & Herzegovina":"🇧🇦","Qatar":"🇶🇦","Switzerland":"🇨🇭","Brazil":"🇧🇷","Morocco":"🇲🇦","Haiti":"🇭🇹","Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","USA":"🇺🇸","Paraguay":"🇵🇾","Australia":"🇦🇺","Türkiye":"🇹🇷","Germany":"🇩🇪","Curaçao":"🇨🇼","Côte d'Ivoire":"🇨🇮","Ecuador":"🇪🇨","Netherlands":"🇳🇱","Japan":"🇯🇵","Sweden":"🇸🇪","Tunisia":"🇹🇳","Belgium":"🇧🇪","Egypt":"🇪🇬","Iran":"🇮🇷","New Zealand":"🇳🇿","Spain":"🇪🇸","Cape Verde":"🇨🇻","Saudi Arabia":"🇸🇦","Uruguay":"🇺🇾","France":"🇫🇷","Senegal":"🇸🇳","Iraq":"🇮🇶","Norway":"🇳🇴","Argentina":"🇦🇷","Algeria":"🇩🇿","Austria":"🇦🇹","Jordan":"🇯🇴","Portugal":"🇵🇹","DR Congo":"🇨🇩","Uzbekistan":"🇺🇿","Colombia":"🇨🇴","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Croatia":"🇭🇷","Ghana":"🇬🇭","Panama":"🇵🇦"};
const pct = x => (x==null||isNaN(x) ? '—' : (x*100).toFixed(x>=0.1?0:1)+'%');
const byId = id => document.getElementById(id);
const esc = s => (s==null?'':String(s)).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// SVG flags via flag-icons when an ISO code exists (fixes the desktop emoji→country-code
// fallback); emoji stays as the fallback for any name without one. Decorative (name is adjacent).
const ISO = {"Mexico":"mx","South Africa":"za","South Korea":"kr","Czechia":"cz","Canada":"ca","Bosnia & Herzegovina":"ba","Qatar":"qa","Switzerland":"ch","Brazil":"br","Morocco":"ma","Haiti":"ht","Scotland":"gb-sct","USA":"us","Paraguay":"py","Australia":"au","Türkiye":"tr","Germany":"de","Curaçao":"cw","Côte d'Ivoire":"ci","Ecuador":"ec","Netherlands":"nl","Japan":"jp","Sweden":"se","Tunisia":"tn","Belgium":"be","Egypt":"eg","Iran":"ir","New Zealand":"nz","Spain":"es","Cape Verde":"cv","Saudi Arabia":"sa","Uruguay":"uy","France":"fr","Senegal":"sn","Iraq":"iq","Norway":"no","Argentina":"ar","Algeria":"dz","Austria":"at","Jordan":"jo","Portugal":"pt","DR Congo":"cd","Uzbekistan":"uz","Colombia":"co","England":"gb-eng","Croatia":"hr","Ghana":"gh","Panama":"pa"};
const flag = t => ISO[t] ? `<span class="fl fi fi-${ISO[t]}" aria-hidden="true"></span>` : `<span class="fl" aria-hidden="true">${FLAG[t]||'🏳️'}</span>`;
const team = t => `${flag(t)}<span class="nm">${esc(t)}</span>`;
let followTeam = DATA.teams.some(t=>t.team==='England') ? 'England' : DATA.teams[0].team;

// timestamps: render the build's UTC epoch in the VIEWER's own local clock + "x ago",
// so it's accurate everywhere regardless of where the build ran.
function fmtLocal(ep){if(!ep)return null;
 return new Date(ep*1000).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});}
function relTime(ep){if(!ep)return '';let s=Math.floor(Date.now()/1000-ep);if(s<0)s=0;
 if(s<60)return 'just now';if(s<3600)return Math.floor(s/60)+' min ago';
 if(s<86400)return Math.floor(s/3600)+'h ago';return Math.floor(s/86400)+'d ago';}
function renderPill(){const ep=DATA.generated_epoch;
 byId('genpill').innerHTML = ep ? `🗓 updated ${esc(fmtLocal(ep))} · ${relTime(ep)}` : ('🗓 updated '+esc(DATA.generated));}
renderPill(); setInterval(renderPill, 60000);
byId('simpill').innerHTML = '🎲 '+DATA.n_sims.toLocaleString()+' simulations';

// poll the deployed version.json; if a newer build exists than this page, show the refresh bar.
let _liveEp=0,_dismissEp=(()=>{try{return +localStorage.getItem('wc-dismiss-ep')||0}catch(e){return 0}})();
async function checkForUpdate(){const ep=DATA.generated_epoch;
 if(!ep||location.protocol==='file:')return;            // no manifest to fetch for local-file opens
 try{const r=await fetch('version.json?cb='+Date.now(),{cache:'no-store'});if(!r.ok)return;
  const v=await r.json();
  if(v&&v.generated_epoch&&v.generated_epoch>ep&&v.generated_epoch>_dismissEp){
   _liveEp=v.generated_epoch;byId('updatebar').hidden=false;}
 }catch(e){/* offline or blocked — ignore */}}
function dismissUpdate(){_dismissEp=_liveEp;try{localStorage.setItem('wc-dismiss-ep',_liveEp)}catch(e){}byId('updatebar').hidden=true;}
// force a cache-busting reload so we get the fresh HTML past the GitHub Pages/CDN cache
function doRefresh(){location.replace(location.pathname+'?v='+(_liveEp||Math.floor(Date.now()/1000)));}
setInterval(checkForUpdate, 180000); checkForUpdate();

/* theme toggle */
function setTheme(t){document.documentElement.setAttribute('data-theme',t);try{localStorage.setItem('wc-theme',t)}catch(e){}
 const b=byId('themebtn');b.textContent=t==='dark'?'☀️':'🌙';
 b.setAttribute('aria-pressed',t==='dark');b.setAttribute('aria-label',t==='dark'?'Switch to light mode':'Switch to dark mode');}
setTheme(document.documentElement.getAttribute('data-theme')||'light');
byId('themebtn').onclick=()=>setTheme(document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark');

/* tabs */
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on'));
 document.querySelectorAll('section').forEach(x=>x.classList.remove('on'));
 b.classList.add('on'); byId(b.dataset.t).classList.add('on');
 if(b.dataset.t==='brackettree') btFit();
 window.scrollTo({top:0,behavior:'smooth'});
});

/* follow-team selector */
function buildFollow(){
 const sel=byId('followsel');
 sel.innerHTML=DATA.teams.slice().sort((a,b)=>a.team.localeCompare(b.team))
   .map(t=>`<option value="${esc(t.team)}"${t.team===followTeam?' selected':''}>${FLAG[t.team]||'🏳️'} ${esc(t.team)}</option>`).join('');
 sel.onchange=()=>{followTeam=sel.value;renderBracket();renderBracketTree();renderYourTeam();renderTeams();};
}

/* round structure */
const ROUND_ORDER={
 R32:[74,77,73,75,83,84,81,82,76,78,79,80,86,88,85,87],
 R16:[89,90,93,94,91,92,95,96],QF:[97,98,99,100],SF:[101,102],F:[104]
};
const RKS=['R32','R16','QF','SF','F'];
const RCLASS={R32:'',R16:'r16',QF:'qf',SF:'sf',F:'fin'};
const RLABEL={R32:'Round of 32',R16:'Round of 16',QF:'Quarterfinals',SF:'Semifinals',F:'Final'};
const RVAR={R32:'--r32',R16:'--r16',QF:'--qf',SF:'--sf',F:'--fin'};
function roundKey(no){if(no<89)return'R32';if(no<97)return'R16';if(no<101)return'QF';if(no<103)return'SF';return'F';}
// chronological sort key from a match's "Jun 28" + "3:00 PM" strings (kickoff order)
const MONTHS={Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11};
function kickoffKey(no){
 const m=DATA.matches[String(no)];if(!m)return 0;
 const dm=(m.date||'').match(/([A-Za-z]+)\s+(\d+)/);
 let k=dm?((MONTHS[dm[1]]??0)*100+(+dm[2]))*10000:0;
 const tm=(m.time||'').match(/(\d+):(\d+)\s*(AM|PM)/i);
 if(tm){let h=(+tm[1])%12;if(/pm/i.test(tm[3]))h+=12;k+=h*100+(+tm[2]);}
 return k;
}
let curRound='R32';
// Bracket tab is fixed to date (kickoff) order — the dedicated Bracket tree tab now carries
// the slot-structure view. Match numbers for a round, in chronological kickoff order.
function roundCards(rk){return ROUND_ORDER[rk].slice().sort((x,y)=>kickoffKey(x)-kickoffKey(y));}

/* team-path helper: most-likely box per round for any team (client-side) */
function teamObj(name){return DATA.teams.find(t=>t.team===name);}
function teamPath(name){
 const t=teamObj(name); const out={}; if(!t)return out;
 const ap=t.appear||{};
 const ranges={R32:[73,89],R16:[89,97],QF:[97,101],SF:[101,103],F:[104,105]};
 for(const rk in ranges){const[a,b]=ranges[rk];let best=null,bp=-1;
  for(let m=a;m<b;m++){const p=ap[String(m)];if(p!=null&&p>bp){bp=p;best=m;}}
  if(best!=null)out[rk]={match:best,p:bp};}
 return out;
}
function followSet(){return new Set(Object.values(teamPath(followTeam)).map(x=>x.match));}

/* confidence ring */
function ring(p,varName){
 const C=2*Math.PI*13, dash=Math.max(0,Math.min(1,p))*C;
 const col=`var(${varName})`;
 return `<div class="ring"><svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
  <circle cx="20" cy="20" r="13" fill="none" stroke="var(--track)" stroke-width="5"/>
  <circle cx="20" cy="20" r="13" fill="none" stroke="${col}" stroke-width="5" stroke-linecap="round"
   stroke-dasharray="${dash.toFixed(1)} ${C.toFixed(1)}" transform="rotate(-90 20 20)"/></svg>
  <div class="pc">${pct(p)}</div><div class="lb">⚔ matchup</div></div>`;
}

/* ---- MOVEMENT / WHAT CHANGED ---- */
function vsFlags(s){if(!s||s==='TBD')return '<span class="muted">TBD</span>';
 const p=s.split(' vs '); return p.map(x=>`${flag(x.trim())} ${esc(x.trim())}`).join(' <span class="muted">vs</span> ');}
function renderChanges(){
 const el=byId('changes'),c=DATA.changes;
 if(!c){el.style.display='none';return;}
 if(c.first_run){el.innerHTML=`<div class="chhead"><span class="t">🎉 Baseline build</span></div><div class="chbody"><div class="crow"><div class="cbody muted">Nothing to compare yet — check back after the next nightly rebuild.</div></div></div>`;return;}
 const since=c.prev_generated_epoch?`<span class="since">since ${esc(fmtLocal(c.prev_generated_epoch))}</span>`:(c.prev_generated?`<span class="since">since ${esc(c.prev_generated)}</span>`:'');
 const rows=[];
 // auto headline
 let hl='';
 if(c.matchups&&c.matchups.length)hl=`${c.matchups.length} bracket matchup${c.matchups.length>1?'s':''} shifted since yesterday`;
 else if(c.title_movers&&c.title_movers.length){const m=c.title_movers[0];hl=`${m.team} ${m.new>=m.old?'climbing':'sliding'} in the title race`;}
 else if(c.new_results&&c.new_results.length)hl=`${c.new_results.length} new result${c.new_results.length>1?'s':''} in`;
 else hl='No material changes since the last rebuild';
 if(c.new_results&&c.new_results.length)
  rows.push(crow('res','New results',c.new_results.map(r=>{
   const m=r.match(/^(.*?) (\d+-\d+) (.*?) \((.*)\)$/);
   return m?`${flag(m[1])} ${esc(m[1])} <b>${m[2]}</b> ${flag(m[3])} ${esc(m[3])} <span class="muted">${esc(m[4])}</span>`:esc(r);
  }).map(x=>`<div class="mvrow">${x}</div>`).join('')));
 if(c.matchups&&c.matchups.length)
  rows.push(crow('flip','Matchups changed ('+c.matchups.length+')',c.matchups.map(x=>
   `<div class="mvitem">
     <div class="mvrow"><span>${vsFlags(x.old)}${x.old_p!=null?` <span class="muted">(${pct(x.old_p)})</span>`:''} <span class="arrow">→</span> <b>${vsFlags(x.new)}</b>${x.new_p!=null?` <span class="muted">(${pct(x.new_p)})</span>`:''}</span>
      <span class="where">·  M${x.match} ${esc(x.round)} · ${esc(x.city)} ${esc(x.date)}</span></div>
     ${x.why?`<div class="why">${whyHtml(x.why)}</div>`:''}
     ${whyChips(x)}
    </div>`).join('')));
 if(c.england_path&&c.england_path.length)
  rows.push(crow('route','🏴󠁧󠁢󠁥󠁮󠁧󠁿 England route',c.england_path.map(x=>`<div class="mvrow">${esc(x.round)}: <span class="muted">${esc(x.old)}</span> <span class="arrow">→</span> <b>${esc(x.new)}</b></div>`).join('')));
 if(c.opponents&&c.opponents.length)
  rows.push(crow('route','🏴󠁧󠁢󠁥󠁮󠁧󠁿 England opponent',c.opponents.map(x=>`<div class="mvrow">${esc(x.round)}: ${flag(x.old)} ${esc(x.old)} <span class="arrow">→</span> ${flag(x.new)} <b>${esc(x.new)}</b></div>`).join('')));
 if(c.england_outlook&&c.england_outlook.length)
  rows.push(crow('look','🏴󠁧󠁢󠁥󠁮󠁧󠁿 England outlook',c.england_outlook.map(x=>{const u=x.new>=x.old;return `<div class="mvrow">${esc(x.metric)} <span class="muted">${pct(x.old)}</span> <span class="${u?'up':'down'}">→ ${pct(x.new)} ${u?'▲':'▼'}</span></div>`;}).join('')));
 if(c.title_movers&&c.title_movers.length)
  rows.push(crow('title','Title movers',c.title_movers.slice(0,6).map(x=>{const u=x.new>=x.old;return `<div class="mvrow">${flag(x.team)} ${esc(x.team)} <span class="muted">${pct(x.old)}</span> <span class="${u?'up':'down'}">→ ${pct(x.new)} ${u?'▲':'▼'}</span></div>`;}).join('')));
 const body = rows.length?rows.join(''):`<div class="crow"><div class="cbody muted">Odds may have nudged, but no tracked matchup, route, or title moved past the reporting threshold.</div></div>`;
 el.innerHTML=`<div class="chhead"><span class="t">🔔 Today's movement</span> ${since}
   <button class="chtoggle" id="chtoggle" type="button" aria-expanded="true" aria-controls="chbody" aria-label="Collapse Today's movement" onclick="toggleChanges()">▾</button></div>
  <div class="chbody" id="chbody"><div class="crow"><div class="cbody headline">${esc(hl)}.</div></div>
  ${c.summary?`<div class="crow"><div class="cbody ctx">${esc(c.summary)}</div></div>`:''}${body}</div>`;
 let mvCol=false;try{mvCol=localStorage.getItem('wc-mv-collapsed')==='1'}catch(e){}
 if(mvCol)setChangesCollapsed(true);
}
// collapse/expand the movement card; persists across reloads
function setChangesCollapsed(col){
 const el=byId('changes');if(!el)return;
 el.classList.toggle('collapsed',col);
 const b=byId('chtoggle');
 if(b){b.setAttribute('aria-expanded',(!col).toString());
  b.setAttribute('aria-label',(col?'Expand':'Collapse')+" Today's movement");}
 try{localStorage.setItem('wc-mv-collapsed',col?'1':'0')}catch(e){}
}
function toggleChanges(){setChangesCollapsed(!byId('changes').classList.contains('collapsed'));}
function crow(cls,tag,inner){return `<div class="crow"><span class="ctag ${cls}">${tag}</span><div class="cbody">${inner}</div></div>`;}
// bold the "who moved" lead-in of a why sentence, leave the cause/confidence muted
function whyHtml(why){const i=why.indexOf(' — ');
 return i<0?esc(why):`<b>${esc(why.slice(0,i))}</b>${esc(why.slice(i))}`;}
// the concrete drivers the why sentence pins this flip on: the result(s), the title-odds
// mover(s), any re-priced line — then a dashed SCOPE chip (which groups can still land a
// team here) shown as context, visibly distinct so it never reads as the cause.
function whyChips(x){
 const d=x.drivers||{},chips=[];
 (d.results||[]).forEach(r=>chips.push(`<span class="dchip res">⚽ ${flag(r.h)} ${esc(r.h)} ${r.hg}–${r.ag} ${esc(r.a)} ${flag(r.a)}</span>`));
 (d.odds||[]).forEach(m=>chips.push(`<span class="dchip ${m.dir}">${m.dir==='up'?'▲':'▼'} ${flag(m.team)} ${esc(m.team)} ${pct(m.old)}→${pct(m.new)}</span>`));
 (d.lines||[]).forEach(l=>chips.push(`<span class="dchip">💱 ${esc(l.h)}–${esc(l.a)} re-priced</span>`));
 const g=x.source_groups||[];
 const scope=g.length>8?'open to the whole field':(g.length>2?'open to Groups '+esc(g.join('/')):'');
 if(scope)chips.push(`<span class="dchip reach" title="Teams from these groups can still reach this box — context, not the cause">🎯 ${scope}</span>`);
 return chips.length?`<div class="chips">${chips.join('')}</div>`:'';
}

/* ---- BRACKET ---- */
function renderRoundNav(){
 byId('roundnav').innerHTML=RKS.map(rk=>
  `<button class="rbtn${rk===curRound?' on':''}" onclick="showRound('${rk}')"><span class="dot" style="background:var(${RVAR[rk]})"></span>${RLABEL[rk]}</button>`).join('');
}
function showRound(rk){curRound=rk;renderRoundNav();
 document.querySelectorAll('.col').forEach(c=>c.classList.toggle('show',c.dataset.rk===rk));
 const col=document.querySelector('.col[data-rk="'+rk+'"]');
 if(col&&window.matchMedia('(min-width:920px)').matches)col.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'});
}
function matchCard(no){
 const m=DATA.matches[String(no)];const rk=roundKey(no);
 const top=m.top_pairs&&m.top_pairs[0];
 const fset=followSet();const foc=fset.has(no);
 const teamsHtml=top?
  `<div class="tm">${team(top.a)}</div><div class="vsbar">vs</div><div class="tm">${team(top.b)}</div>`
  :`<div class="tm muted">To be decided</div>`;
 return `<div class="m ${RCLASS[rk]}${foc?' follow':''}" data-no="${no}" role="button" tabindex="0" aria-label="${esc(m.round)} · ${esc(m.city)} ${esc(m.date)} — full odds">
  <div class="mh"><span class="where">📍 ${esc(m.city)}</span><span class="when">${esc(m.date)} · ${esc(m.time)}</span></div>
  <div class="mrow"><div class="teams">${teamsHtml}</div>${top?ring(top.p,RVAR[rk]):''}</div>
  ${foc?`<span class="followtag">⭐ ${esc(followTeam)} projected here</span>`:''}</div>`;
}
function renderBracket(){
 const brk=byId('brk');brk.innerHTML='';
 for(const rk of RKS){
  const col=document.createElement('div');col.className='col'+(rk===curRound?' show':'');col.dataset.rk=rk;
  col.innerHTML=`<div class="colhead"><span class="dot" style="background:var(${RVAR[rk]})"></span>${RLABEL[rk]}</div>`
   +roundCards(rk).map(matchCard).join('');
  brk.appendChild(col);
 }
 const tp=DATA.matches['103'];
 if(tp)byId('tpline').textContent=`${tp.city} · ${tp.date} · ${tp.time} — losing semifinalists.`;
}

/* ---- BRACKET TREE (mirrored, connected, driven by the real bracket) ---- */
// follow a team from anywhere (e.g. tapping a tree box); keeps the dropdown in sync
function setFollow(name){if(!name)return;followTeam=name;const sel=byId('followsel');if(sel)sel.value=name;
 renderBracket();renderBracketTree();renderYourTeam();renderTeams();}
const BT={boxW:132,boxH:56,hGap:34,rowUnit:72,leftPad:40,rightPad:40,topPad:96};
BT.W=BT.leftPad+9*BT.boxW+8*BT.hGap+BT.rightPad;     // 1540
BT.H=BT.topPad+7.5*BT.rowUnit+BT.boxH/2+40;          // 704
const btColX=i=>BT.leftPad+BT.boxW/2+i*(BT.boxW+BT.hGap);
const btRowY=r=>BT.topPad+r*BT.rowUnit;
const BT_ROWS={r32:[0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5],r16:[1,3,5,7],qf:[2,6],sf:[4],fin:[4]};
const btTeams=no=>{const m=DATA.matches[String(no)];const tp=m&&m.top_pairs&&m.top_pairs[0];return tp?{a:tp.a,b:tp.b,p:tp.p}:null;};
// build the 9 columns (mirrored) + parent/child links, all from ROUND_ORDER's bracket order
function btBuild(){
 const R=ROUND_ORDER;
 const def=[['r32',R.R32.slice(0,8),BT_ROWS.r32,'L',0],['r16',R.R16.slice(0,4),BT_ROWS.r16,'L',1],
  ['qf',R.QF.slice(0,2),BT_ROWS.qf,'L',2],['sf',R.SF.slice(0,1),BT_ROWS.sf,'L',3],
  ['fin',R.F.slice(0,1),BT_ROWS.fin,'C',4],['sf',R.SF.slice(1,2),BT_ROWS.sf,'R',5],
  ['qf',R.QF.slice(2,4),BT_ROWS.qf,'R',6],['r16',R.R16.slice(4,8),BT_ROWS.r16,'R',7],
  ['r32',R.R32.slice(8,16),BT_ROWS.r32,'R',8]];
 const cb=def.map(([round,nums,rows,side,col])=>nums.map((no,i)=>(
   {no,round,side,col,idx:i,cx:btColX(col),cy:btRowY(rows[i])})));
 const boxes=cb.flat(),links=[];
 const L=(child,parent,side)=>links.push({child,parent,side});
 const [Lr32,Lr16,Lqf,Lsf,Fin,Rsf,Rqf,Rr16,Rr32]=cb;
 Lr16.forEach((p,j)=>{L(Lr32[2*j],p,'L');L(Lr32[2*j+1],p,'L');});
 Lqf.forEach((p,k)=>{L(Lr16[2*k],p,'L');L(Lr16[2*k+1],p,'L');});
 L(Lqf[0],Lsf[0],'L');L(Lqf[1],Lsf[0],'L');L(Lsf[0],Fin[0],'L');
 Rr16.forEach((p,j)=>{L(Rr32[2*j],p,'R');L(Rr32[2*j+1],p,'R');});
 Rqf.forEach((p,k)=>{L(Rr16[2*k],p,'R');L(Rr16[2*k+1],p,'R');});
 L(Rqf[0],Rsf[0],'R');L(Rqf[1],Rsf[0],'R');L(Rsf[0],Fin[0],'R');
 return {boxes,links,Fin:Fin[0]};
}
function btPath(l){const c=l.child,p=l.parent;
 if(l.side==='L'){const x1=c.cx+BT.boxW/2,x2=p.cx-BT.boxW/2,mx=(x1+x2)/2;return `M${x1},${c.cy} H${mx} V${p.cy} H${x2}`;}
 const x1=c.cx-BT.boxW/2,x2=p.cx+BT.boxW/2,mx=(x1+x2)/2;return `M${x1},${c.cy} H${mx} V${p.cy} H${x2}`;}
function btBoxHtml(b,info){
 const t=info.teams[b.no],stripe=`var(--${b.round})`,win=info.winner[b.no];
 const foc=!!t&&(t.a===followTeam||t.b===followTeam);
 let s=`left:${b.cx-BT.boxW/2}px;top:${b.cy-BT.boxH/2}px;width:${BT.boxW}px;height:${BT.boxH}px;`;
 if(b.side==='C')s+='border-left:4px solid var(--fin);border-right:4px solid var(--fin);';
 else if(b.side==='L')s+=`border-left:4px solid ${stripe};`;
 else s+=`border-right:4px solid ${stripe};`;
 const rowH=(BT.boxH-1)/2;
 const row=(nm,div)=>{
  if(!nm)return `<div class="bt-row lose${div?' div':''}" style="height:${rowH}px"><span class="bt-nm">—</span></div>`;
  const isFoc=nm===followTeam,isWin=nm===win,cls=isFoc?'foc':(isWin?'win':'lose');
  const mark=isFoc?'<span class="bt-star">★</span>':(isWin?`<span class="bt-tk" style="background:${stripe}"></span>`:'');
  return `<div class="bt-row ${cls}${div?' div':''}" style="height:${rowH}px">${flag(nm)}<span class="bt-nm">${esc(nm)}</span>${mark}</div>`;};
 const inner=t?row(t.a,true)+row(t.b,false):row(null,true)+row(null,false);
 const fol=t?esc(win||t.a):'';
 return `<div class="bt-box${foc?' foc':''}" style="${s}"${fol?` data-btfollow="${fol}"`:''}>${inner}</div>`;
}
function renderBracketTree(){
 const canvas=byId('btCanvas');if(!canvas)return;
 const {boxes,links,Fin}=btBuild();
 const teams={},winner={};
 boxes.forEach(b=>{teams[b.no]=btTeams(b.no);});
 const champObj=DATA.teams.slice().sort((a,b)=>(b.p_champ||0)-(a.p_champ||0))[0];
 const champ=champObj?champObj.team:null;
 const teamsOf=no=>{const t=teams[no];return t?[t.a,t.b]:[];};
 // the projected advancer in each box = the team that also shows up in the parent box's pair
 links.forEach(l=>{const ct=teams[l.child.no];if(!ct){winner[l.child.no]=null;return;}
  const pt=teamsOf(l.parent.no);winner[l.child.no]=pt.includes(ct.a)?ct.a:(pt.includes(ct.b)?ct.b:null);});
 const ft=teams[Fin.no];if(ft)winner[Fin.no]=(ft.a===champ||ft.b===champ)?champ:ft.a;
 const info={teams,winner};
 const inFoc=no=>{const t=teams[no];return !!t&&(t.a===followTeam||t.b===followTeam);};
 const hot=l=>inFoc(l.child.no)&&inFoc(l.parent.no);
 const champHi=champ===followTeam,spineTop=BT.topPad+44,finalTop=Fin.cy-BT.boxH/2;
 const svg=`<svg class="bt-svg" width="${BT.W}" height="${BT.H}" viewBox="0 0 ${BT.W} ${BT.H}">`
  +links.filter(l=>!hot(l)).map(l=>`<path d="${btPath(l)}" fill="none" stroke="var(--bd2)" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round"/>`).join('')
  +`<path d="M${Fin.cx},${spineTop} V${finalTop}" fill="none" stroke="${champHi?'var(--accent)':'var(--bd2)'}" stroke-width="${champHi?2.6:1.4}" stroke-linecap="round"/>`
  +links.filter(hot).map(l=>`<path d="${btPath(l)}" fill="none" stroke="var(--accent)" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>`).join('')+`</svg>`;
 const COLDEF=[['R32','Round of 32',0],['R16','Round of 16',1],['QF','Quarterfinal',2],['SF','Semifinal',3],['SF','Semifinal',5],['QF','Quarterfinal',6],['R16','Round of 16',7],['R32','Round of 32',8]];
 const RVARC={R32:'--r32',R16:'--r16',QF:'--qf',SF:'--sf'};
 const labels=COLDEF.map(([rk,lab,col])=>`<div class="bt-collabel" style="left:${btColX(col)-BT.boxW/2}px;top:26px;width:${BT.boxW}px"><span class="dot" style="background:var(${RVARC[rk]})"></span><span class="lb">${lab}</span></div>`).join('');
 const trophy=`<div class="bt-champ" style="left:${BT.W/2-120}px;top:28px;width:240px">`
  +`<svg width="44" height="48" viewBox="0 0 58 62" style="display:block;margin:0 auto 3px" aria-hidden="true"><path d="M11 6 H47 V18 C47 31 39 37 29 37 C19 37 11 31 11 18 Z" fill="var(--signal)"/><path d="M11 9 C2 9 3 24 15 26" fill="none" stroke="var(--signal)" stroke-width="3.5" stroke-linecap="round"/><path d="M47 9 C56 9 55 24 43 26" fill="none" stroke="var(--signal)" stroke-width="3.5" stroke-linecap="round"/><rect x="26" y="37" width="6" height="11" fill="var(--signal)"/><rect x="17" y="48" width="24" height="5" rx="2" fill="var(--signal)"/><rect x="21" y="54" width="16" height="6" rx="2" fill="var(--signal)"/></svg>`
  +`<div class="cap">Projected champion</div><div class="row">${champ?flag(champ):''}<span class="nm">${esc(champ||'TBD')}</span></div>`
  +`<div class="pc">Wins it all · ${champObj?pct(champObj.p_champ):'—'}</div></div>`;
 canvas.style.width=BT.W+'px';canvas.style.height=BT.H+'px';
 canvas.innerHTML=svg+labels+trophy+boxes.map(b=>btBoxHtml(b,info)).join('');
 canvas.querySelectorAll('[data-btfollow]').forEach(el=>el.onclick=()=>setFollow(el.dataset.btfollow));
 btFit();
}
function btFit(){const canvas=byId('btCanvas'),scroll=byId('btScroll'),sizer=byId('btSizer');
 if(!canvas||!scroll||!sizer)return;
 let s=(scroll.clientWidth-14)/BT.W; if(s>1)s=1; if(s<0.6||!(s>0))s=0.6;
 canvas.style.transform='scale('+s+')';
 sizer.style.width=(BT.W*s)+'px';sizer.style.height=(BT.H*s)+'px';}
window.addEventListener('resize',()=>{if(byId('btCanvas'))btFit();});

function openMatch(no){
 const m=DATA.matches[String(no)];if(!m)return;
 const tt=m.top_teams||[],tp=m.top_pairs||[];
 let h=`<button class="close" onclick="closeM()" aria-label="Close">×</button>`;
 h+=`<h3>${esc(m.round)} · Match ${no}</h3>`;
 h+=`<div class="muted">📍 ${esc(m.city)} · ${esc(m.date)} · ${esc(m.time)} ET · <b style="color:var(--bad-ink)">elimination</b></div>`;
 h+=`<div class="muted" style="margin:6px 0 14px">Slot: ${esc(m.slot)}</div>`;
 h+=`<b>Most likely to appear here</b>`;
 if(!tt.length){h+=`<div class="muted">No projection for this box yet.</div>`;}
 else{const mx=Math.max(...tt.map(x=>x.p));h+=tt.map(t=>probRow(team(t.team),t.p,mx)).join('');}
 if(tp.length){h+=`<b style="display:block;margin-top:16px">Most likely exact matchups</b>`;
  h+=tp.map(p=>`<div class="prob"><span class="nm" style="width:auto;flex:1">${team(p.a)} <span class="muted">vs</span> ${team(p.b)}</span><span class="pc">${pct(p.p)}</span></div>`).join('');}
 showModal(h);
}
function probRow(label,p,mx){const w=Math.max(2,p/mx*100);
 return `<div class="prob"><span class="nm">${label}</span><span class="track"><span class="fill" style="width:${w}%"></span></span><span class="pc">${pct(p)}</span></div>`;}
let lastFocus=null;
function showModal(html){lastFocus=document.activeElement;byId('mbox').innerHTML=html;
 const m=byId('modal');m.classList.add('on');m.setAttribute('aria-hidden','false');
 const c=byId('mbox').querySelector('.close');if(c)c.focus();}
function closeM(){const m=byId('modal');m.classList.remove('on');m.setAttribute('aria-hidden','true');
 if(lastFocus&&lastFocus.focus)lastFocus.focus();}
byId('modal').onclick=e=>{if(e.target.id==='modal')closeM();};
document.addEventListener('click',e=>{
 const mc=e.target.closest('[data-no]');if(mc){openMatch(+mc.dataset.no);return;}
 const tl=e.target.closest('[data-team]');if(tl){teamMatches(tl.dataset.team);}});
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'&&byId('modal').classList.contains('on')){closeM();return;}
 if(e.key==='Enter'||e.key===' '){const el=e.target.closest('[data-no],[data-team]');
  if(el){e.preventDefault();if(el.dataset.no!=null)openMatch(+el.dataset.no);else teamMatches(el.dataset.team);}}});

/* ---- YOUR TEAM ---- */
function renderYourTeam(){
 const t=teamObj(followTeam);if(!t){byId('yt').innerHTML='';return;}
 const path=teamPath(followTeam);
 const out=Math.max(0,1-(t.p_advance||0));
 const fin=[['Win group',t.p_win_group,'var(--good-ink)'],['Runner-up',t.p_runner,'var(--blue-ink)'],
   ['3rd & qualify',t.p_third_q,'var(--gold-ink)'],['Out in groups',out,'var(--bad-ink)']];
 const reach=[['Reach R16',t.p_r16],['Reach QF',t.p_qf],['Reach SF',t.p_sf],['Reach final',t.p_final],['Win it all',t.p_champ]];
 const steps=RKS.filter(rk=>path[rk]).map(rk=>{
  const x=path[rk],m=DATA.matches[String(x.match)];
  let opp='';const tt=(m.top_teams||[]).find(q=>q.team!==followTeam);
  if(tt)opp=`<div class="op">vs ${team(tt.team)} <span class="muted">${pct(tt.p)}</span></div>`;
  return `<div class="step"><div class="r">${RLABEL[rk]} · most likely</div>
   <div class="c">📍 ${esc(m.city)}</div><div class="d">M${x.match} · ${esc(m.date)} · ${esc(m.time)} ET</div>
   ${opp}<div class="pp">${pct(x.p)} ${esc(followTeam)} plays here</div></div>`;
 }).join('');
 const cities=RKS.filter(rk=>path[rk]).map(rk=>DATA.matches[String(path[rk].match)].city);
 const uniqCities=[...new Set(cities)];
 byId('yt').innerHTML=`<div class="card">
  <h3 style="margin-top:0">${flag(followTeam)} ${esc(followTeam)} — projected route &amp; where to be</h3>
  <div class="muted">Group ${esc(t.group)} · rating ${t.rating} · champion ${pct(t.p_champ)}. Pick another side with ⭐ Follow a team up top.</div>
  <div class="statrow">${fin.map(([l,v,c])=>`<div class="stat"><div class="v" style="color:${c}">${pct(v||0)}</div><div class="l">${l}</div></div>`).join('')}</div>
  <div class="path">${steps||'<div class="muted">No likely knockout route yet.</div>'}</div>
  <div class="statrow" style="margin-top:14px">${reach.map(([l,v])=>`<div class="stat"><div class="v">${pct(v||0)}</div><div class="l">${l}</div></div>`).join('')}</div>
  <p class="muted" style="margin-top:14px">Where to be for ${esc(followTeam)}'s likeliest knockout games: <b>${uniqCities.map(esc).join(' → ')||'TBD'}</b>. Tap any box in the Bracket tab (⭐ marks their projected slots) for the full odds.</p>
 </div>`;
}

/* ---- TEAMS ---- */
// Champion column = Polymarket title odds (de-vigged), refreshed every 3h by the
// rebuild (odds.json → build.py → calibration.market). Only the ~20 teams Polymarket
// lists get a value; the rest stay undefined and render as "—". The model's own champ %
// still appears in Method (calibration table) and each team's popup.
const PM_CHAMP=Object.fromEntries((DATA.calibration||[]).filter(c=>c&&c.market!=null).map(c=>[c.team,c.market]));
DATA.teams.forEach(t=>{t.pm_champ=PM_CHAMP[t.team];});
let sortKey='pm_champ',sortDir=-1;
const COLS=[['team','Team'],['group','Grp'],['rating','Rtg'],['p_win_group','Win grp'],
 ['p_runner','RU'],['p_advance','Reach R32'],['p_r16','R16'],['p_qf','QF'],['p_sf','SF'],
 ['p_final','Final'],['pm_champ','Champion','Polymarket']];
function renderTeams(){
 const q=(byId('tsearch').value||'').toLowerCase();
 // null/undefined (teams Polymarket doesn't list) sort to the bottom; string cols are never null.
 const rows=DATA.teams.filter(t=>t.team.toLowerCase().includes(q))
  .sort((a,b)=>{let x=a[sortKey],y=b[sortKey];if(x==null)x=-Infinity;if(y==null)y=-Infinity;
   return sortDir*((x>y)?1:(x<y)?-1:0);});
 let h='<tr>'+COLS.map(c=>{const arr=sortKey===c[0]?(sortDir<0?' ▾':' ▴'):'';
   const sub=c[2]?`<span class="thsrc">${c[2]}</span>`:'';
   return `<th onclick="setSort('${c[0]}')">${c[1]}${arr}${sub}</th>`;}).join('')+'</tr>';
 h+=rows.map(t=>{
  const cells=COLS.map(c=>{let v=t[c[0]];
   if(c[0]==='team')return `<td><a class="tlink" data-team="${esc(t.team)}" role="button" tabindex="0"><span class="tcell">${team(t.team)}</span></a></td>`;
   if(c[0]==='group'||c[0]==='rating')return `<td>${esc(v)}</td>`;
   return `<td>${pct(v)}</td>`;}).join('');
  return `<tr class="${t.team===followTeam?'foc':''}">${cells}</tr>`;}).join('');
 byId('ttbl').innerHTML=h;
}
function setSort(k){if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=-1;}renderTeams();}
function teamMatches(name){
 const t=teamObj(name);if(!t)return;
 let h=`<button class="close" onclick="closeM()" aria-label="Close">×</button><h3>${flag(name)} ${esc(name)}</h3>`;
 h+=`<div class="muted">Group ${esc(t.group)} · rating ${t.rating} · champion ${pct(t.p_champ)}</div>`;
 h+=`<div class="muted" style="margin:6px 0 14px">Win group ${pct(t.p_win_group)} · runner-up ${pct(t.p_runner)} · 3rd&amp;qualify ${pct(t.p_third_q)} · reach R32 ${pct(t.p_advance)}</div>`;
 h+=`<b>Probability of playing in each knockout match</b>`;
 const ap=Object.entries(t.appear||{}).sort((a,b)=>a[0]-b[0]);
 const mx=ap.length?Math.max(...ap.map(x=>x[1])):1;
 h+=ap.map(([no,p])=>{const m=DATA.matches[no];
  return probRow(`M${no} ${esc(m.round.replace('Round of','R'))} · ${esc(m.city)}`,p,mx);}).join('');
 showModal(h);
}

/* ---- GROUPS ---- */
function renderGroups(){
 const tn=Object.fromEntries(DATA.teams.map(t=>[t.team,t]));let h='';
 for(const g of Object.keys(DATA.groups)){
  const rows=DATA.standings[g];
  h+=`<div class="card"><div class="gtitle">Group ${g}</div><div class="gscroll"><table class="gtbl">
   <tr><th>Team</th><th>P</th><th>Pts</th><th>GD</th><th>Win</th><th>Adv</th></tr>`;
  h+=rows.map(r=>{const t=tn[r.team];
   const advc=t.p_advance>=.65?'q1':t.p_advance>=.4?'q2':t.p_advance>=.2?'q3':'';
   return `<tr><td><span class="tcell">${team(r.team)}${r.team===followTeam?' ⭐':''}</span></td><td>${r.mp}</td><td>${r.pts}</td>
    <td>${r.gd>0?'+':''}${r.gd}</td><td>${pct(t.p_win_group)}</td><td class="${advc}">${pct(t.p_advance)}</td></tr>`;}).join('');
  h+=`</table></div></div>`;
 }
 byId('ggrid').innerHTML=h;
}

/* ---- METHOD ---- */
function renderMethod(){
 byId('asm').innerHTML=DATA.assumptions.map(a=>`<li>${esc(a)}</li>`).join('');
 let h='<tr><th>Team</th><th>Polymarket</th><th>Model</th></tr>';
 h+=DATA.calibration.map(c=>`<tr><td><span class="tcell">${team(c.team)}</span></td><td>${pct(c.market)}</td><td>${pct(c.model)}</td></tr>`).join('');
 byId('caltbl').innerHTML=h;
 const mc=DATA.match_calibration||[];const wdl=a=>a.map(x=>pct(x)).join(' / ');
 if(mc.length){
  let m='<tr><th>Game</th><th>Grp</th><th>Market H/D/A</th><th>Model H/D/A</th></tr>';
  m+=mc.map(c=>`<tr><td><span class="tcell">${flag(c.h)} ${esc(c.h)} <span class="muted">v</span> ${flag(c.a)} ${esc(c.a)}</span></td><td>${esc(c.group)}</td><td>${wdl(c.market)}</td><td>${wdl(c.model)}</td></tr>`).join('');
  byId('mcaltbl').innerHTML=m;
 } else {byId('mcalhd').style.display='none';byId('mcaltbl').previousElementSibling.style.display='none';byId('mcaltbl').style.display='none';}
}

buildFollow();renderChanges();renderRoundNav();renderBracket();renderBracketTree();renderYourTeam();
renderTeams();byId('tsearch').oninput=renderTeams;renderGroups();renderMethod();
</script></body></html>"""

# Deploy origin baked in so every rebuild (incl. the nightly one) emits absolute
# Open Graph tags for link previews. Override with WC_SITE_URL when hosting elsewhere;
# set it to "" to fall back to relative paths for purely-local use.
SITE_URL = os.environ.get("WC_SITE_URL", "https://milanpcooper-ui.github.io/world-cup-2026-bracket-model").rstrip("/")
og_image = (SITE_URL + "/og-preview.png") if SITE_URL else "og-preview.png"
og_url = (SITE_URL + "/") if SITE_URL else ""
payload = json.dumps(data)
html = (TEMPLATE.replace("__DATA__", payload)
                .replace("__OGIMAGE__", og_image)
                .replace("__OGURL__", og_url))
outputs = []
# index.html so the hosted site root serves the dashboard directly.
for fname in ("World_Cup_2026_Predictor.html", "index.html"):
    p = os.path.join(HERE, fname)
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    outputs.append((p, round(len(html.encode("utf-8")) / 1024)))
for p, kb in outputs:
    print("Wrote", p, kb, "kb")

# tiny manifest the live page polls to detect a newer build (for the refresh banner)
with open(os.path.join(HERE, "version.json"), "w", encoding="utf-8") as f:
    json.dump({"generated": data.get("generated"), "generated_epoch": data.get("generated_epoch")}, f)
print("Wrote version.json")
