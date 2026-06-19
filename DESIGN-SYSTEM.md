# DESIGN-SYSTEM.md — "Matchday" re-skin mapping

Maps the imported **Matchday** design system onto the existing app's CSS token layer.
This is the Phase 0 deliverable: a token-by-token map, plus the gaps that need your call.

## Sources read

Imported via the exported zip (`World Cup Bracket Design System-handoff.zip`), extracted to
`.design-import/` (git-ignored). The design system is **"Matchday" — editorial-quant / sport-zine**.

**Authoritative files** (the design system proper; `styles.css` is a manifest that `@import`s them):

- `tokens/colors.css` — surfaces, ink, accents, status + ink variants, round arc, gradient, signal (light + dark)
- `tokens/typography.css` — font families, type scale, weights, tracking
- `tokens/spacing.css` — spacing scale, radii, layout breakpoints
- `tokens/effects.css` — shadows, focus ring, border widths, motion
- `tokens/base.css` — resets, body type, `.fl/.fi` flag helper
- `readme.md` — the canonical written spec (adjudicates every ambiguity)

**Superseded** (do not map values from): `uploads/world-cup-redesign.css` — an earlier seed.
The README says Matchday *"replaces the earlier purple→teal / system-font / emoji-flag look,"* and
diverges from the seed on the header (blue field, **not** flattened to panel), the round palette
(cool→hot arc, **not** monochrome), the signal (vermilion reintroduced), and dark mode (warm
near-black `#14120d`, **not** navy). I still use the seed's §3–§7 *selectors* as a guide for which
class-level literals to re-route, because it targets this app's real class names.

## Edit target

Per your decision: edits land in the `TEMPLATE` r-string in **`gen_dashboard.py`** (the single
source of all visual styling), then `python3 gen_dashboard.py` regenerates both `index.html` and
`World_Cup_2026_Predictor.html`. Output stays a single self-contained file — no split, no framework.

---

## 1. Color token remap (design value → existing variable)

Existing variable **names are preserved** (114 call sites depend on them); only their **values**
change. Where the design uses a hyphenated name (`--panel-2`), we keep the existing un-hyphenated
name (`--panel2`) and take the design's value.

### Surfaces, ink, borders

| Existing var | Role | Light: now → **new** | Dark: now → **new** |
|---|---|---|---|
| `--bg` | app background | `#f3f2ff` → **`#f4f1ea`** | `#121130` → **`#14120d`** |
| `--panel` | card surface | `#ffffff` → **`#fffdf8`** | `#1c1a3c` → **`#1d1a13`** |
| `--panel2` | inset/hover surface | `#f4f3ff` → **`#ece6d9`** | `#252247` → **`#26221a`** |
| `--ink` | primary text | `#1b1a2e` → **`#1a1814`** | `#f0eeff` → **`#f3efe4`** |
| `--mut` | secondary text | `#5f5d80` → **`#6f685b`** | `#a3a0c8` → **`#a39b8a`** |
| `--bd` | hairline border | `#e8e6fb` → **`#e2dccd`** | `#2c2956` → **`#2f2a20`** |
| `--bd2` | stronger border | `#cdc8f2` → **`#cabda6`** | `#494383` → **`#483f2c`** |
| `--track` | progress track | `#d7d1f0` → **`#e2dccd`** | `#2a2750` → **`#2f2a20`** |
| `--overlay` | modal scrim | `rgba(27,26,46,.42)` → **`rgba(26,24,20,.46)`** | `rgba(4,6,20,.62)` → **`rgba(6,5,2,.62)`** |
| `--engrow` | followed-row tint | `#fdeaf2` → **`#e7eefc`** | `#33183a` → **`#16213b`** |

### Brand & semantic status

| Existing var | Role | Light: now → **new** | Dark: now → **new** |
|---|---|---|---|
| `--accent` | brand ink-blue | `#6c5ce7` → **`#1f4fd6`** | `#9b8dff` → **`#6f9bff`** |
| `--accent2` | tonal lighter blue | `#00b894` *(green!)* → **`#4a74ec`** | `#2ee6b6` → **`#9bbcff`** |
| `--good` | up / qualified | `#10b981` → **`#1f7a4d`** | `#34d399` → **`#3fbf7f`** |
| `--bad` | down / eliminated | `#ec4476` → **`#c0392f`** | `#ff5d8f` → **`#ff6b5e`** |
| `--gold` | highlight / 3rd | `#f59e0b` → **`#9a6313`** | `#fbbf24` → **`#dca64a`** |
| `--good-ink` | AA text-on-light | `#047857` → **`#1b6b43`** | `#34d399` → **`#3fbf7f`** |
| `--bad-ink` | AA text-on-light | `#be123c` → **`#a93226`** | `#ff7da6` → **`#ff8a80`** |
| `--gold-ink` | AA text-on-light | `#b45309` → **`#7e5012`** | `#fbbf24` → **`#dca64a`** |
| `--teal-ink` | (folded into blue) | `#0f766e` → **`#1f4fd6`** | `#2ee6b6` → **`#6f9bff`** |
| `--blue-ink` | accent-ish ink | `#1d4ed8` → **`#1d4ed8`** *(unchanged light)* | `#7cb0ff` → **`#7cb0ff`** |

### Round-stage arc (cool→hot, lands on signal at Final)

| Existing var | Round | Light: now → **new** | Dark: now → **new** |
|---|---|---|---|
| `--r32` | R32 azure | `#2563eb` → **`#2f6bd6`** | `#60a5fa` → **`#4f7ee6`** |
| `--r16` | R16 indigo | `#0891b2` → **`#5a59d8`** | `#22d3ee` → **`#7b78ec`** |
| `--qf` | QF violet | `#7c3aed` → **`#8b46cf`** | `#a78bfa` → **`#a874e0`** |
| `--sf` | SF magenta | `#d97706` → **`#c83e95`** | `#fbbf24` → **`#e06bb0`** |
| `--fin` | Final vermilion | `#db2777` → **`#ee5a37`** | `#f472b6` → **`#ff7a52`** |

### Chrome & composites

| Existing var | Role | Light: now → **new** | Dark: now → **new** |
|---|---|---|---|
| `--navon` | selected tab bg | `#efeaff` → **`#e7eefc`** | `#2c2960` → **`#1c2742`** |
| `--navonink` | selected tab text | `#4c3fc7` → **`#1a3c97`** | `#cbc3ff` → **`#9bbcff`** |
| `--grad` | header **blue field** | `linear-gradient(105deg,#6d28d9,#7c3aed,#0e7490)` → **`linear-gradient(118deg,#1f4fd6 0%,#1c3fae 100%)`** | purple→teal → **`linear-gradient(118deg,#21407f 0%,#18305f 100%)`** |
| `--shadow` | near-flat elevation | `0 1px 2px rgba(20,18,50,.05),0 10px 30px rgba(76,63,199,.07)` → **`0 1px 1px rgba(26,22,14,.04)`** | `0 1px 2px/.3, 0 12px 34px/.4` → **`0 1px 2px rgba(0,0,0,.4)`** |

`<meta name="theme-color">` literal `#6c5ce7` → **`#1f4fd6`** (meta can't use `var()`).

---

## 2. Design tokens with NO existing home → propose NEW tokens

These exist in the design but have no current variable. All are needed to route bypass literals or
to express the design faithfully. **Proposed additions to `:root` / dark block:**

| New token | Light | Dark | Drives |
|---|---|---|---|
| `--signal` | `#ee5a37` | `#ff7a52` | hot "live/now" pop: reinforces Final; available for live UI |
| `--signal-ink` | `#c0432a` | `#ff8a66` | AA-safe signal text on paper → `.lo-live` (was `--good-ink`) |
| `--signal-pulse` | `rgba(238,90,55,.5)` | `rgba(255,122,82,.5)` | `@keyframes lopulse` start color (was green `rgba(16,185,129,.5)`); fade end = `transparent` |
| `--hero-ink` | `#fbfaf5` | `#f3efe4` | **solid on-gradient text** — replaces `color:#fff` on header / updatebar / iconbtn / pill / followsel |
| `--hero-mut` | `rgba(255,255,255,.9)` | (same) | soft on-gradient text — `.sub`, `.follow label` (was `rgba(255,255,255,.9/.92)`) |
| `--on-fill` | `#ffffff` | `#ffffff` | white text on saturated chips/badges — `.ctag`, `.followtag`, status fills (matches design `Badge`) |
| `--grad-fill` | `rgba(255,255,255,.16)` | (same) | translucent control fill on the field (iconbtn/pill/followsel) |
| `--grad-fill-2` | `rgba(255,255,255,.24)` | (same) | stronger fill (updatebar button) |
| `--grad-fill-3` | `rgba(255,255,255,.32)` | (same) | hover / strongest fill |
| `--grad-bd` | `rgba(255,255,255,.30)` | (same) | hairline border of on-gradient controls |

> The README sanctions the translucent-white controls explicitly: *"Translucency is used only for
> controls on the gradient (white at 16–34% alpha)."* The current spread of alphas
> (.16/.18/.22/.26/.28/.32/.34/.4) consolidates onto `--grad-fill{,-2,-3}` + `--grad-bd` (each within
> the sanctioned 16–34% range; max perceptual shift a few %). No raw literal survives outside the
> token block.

**Optional design tokens (defer unless you want them):** `--shadow-lg` (second elevation, design uses
it for modals only), `--ring-accent` (= existing `.m.follow` inset ring, already hand-written),
`--bd-accent-w:6px` (match-card left stripe width), motion tokens `--ease`/`--dur-*` (existing uses
literal `.25s` etc.).

---

## 3. Existing variables with NO design value → **none**

Every existing variable has a design value (table §1). There are **no "orphan" existing variables**,
so no stop-and-ask on that axis. Good news for a clean value-only remap.

---

## 4. Complete bypass enumeration (every color literal outside the token blocks)

Exhaustive scan of `gen_dashboard.py` (TEMPLATE = lines 15–741; `<style>` = 29–255). The JS region
(256–741) has **zero** color literals; JS `.style.` only sets `display`; inline `style=""` attrs are
layout or already `var()`-based. **All** color bypasses live in `<style>`:

| Line | Literal | → routes to |
|---|---|---|
| 60 | `.updatebar` `color:#fff` | `--hero-ink` |
| 62 | `.updatebar button` `rgba(255,255,255,.22)` bg, `rgba(…,.4)` bd, `color:#fff` | `--grad-fill-2`, `--grad-bd`, `--hero-ink` |
| 64 | `.updatebar button:hover` `rgba(255,255,255,.32)` | `--grad-fill-3` |
| 69 | `header` `color:#fff` | `--hero-ink` |
| 73 | `.iconbtn` `rgba(…,.16)` bg, `rgba(…,.28)` bd, `color:#fff` | `--grad-fill`, `--grad-bd`, `--hero-ink` |
| 75 | `.iconbtn:hover` `rgba(…,.26)` | `--grad-fill-3` |
| 77–78 | `.pill` `rgba(…,.16)` bg, `rgba(…,.22)` bd, `color:#fff` | `--grad-fill`, `--grad-bd`, `--hero-ink` |
| 79 | `.sub` `color:rgba(255,255,255,.92)` | `--hero-mut` |
| 81 | `.follow label` `color:rgba(255,255,255,.9)` | `--hero-mut` |
| 82 | `select#followsel` `rgba(…,.18)` bg, `color:#fff`, `rgba(…,.34)` bd | `--grad-fill`, `--hero-ink`, `--grad-bd` |
| 84 | `select#followsel option{color:#1b1a2e}` | `var(--ink)` |
| 99 | `.chhead` `linear-gradient(100deg,rgba(108,92,231,.14),rgba(6,182,212,.12))` | `var(--panel2)` (flat) |
| 113 | `.ctag` `color:#fff` | `--on-fill` |
| 115–116 | `.ctag.flip #be185d`, `.res #047857`, `.title #b45309`, `.route #1d4ed8`, `.look #7c3aed` | `var(--chip-flip/res/title/route/look)` — fixed AA-safe palette hues (see contrast note) |
| 170 | `.followtag` `color:#fff` (bg already `var(--accent)`) | `--on-fill` |
| 238 | `@keyframes lopulse` green `rgba(16,185,129,.5→0)` | `--signal-pulse` → `transparent` |

**Plus two non-literal semantic touch-ups:**
- `.lo-live{color:var(--good-ink)}` (line ~236) → `var(--signal-ink)` — the design maps "live" to the signal (D6).
- Verify the follow/TeamRoad stat colors injected via `style="color:${c}"` (line ~606) reference
  `var(--…)` tokens, not hex — re-route if any are literal.

## 4b. Radius routing (per the "radius scale only" decision — D5)

Add the radius tokens and route **every** `border-radius` px literal to them, by element role
(from `tokens/spacing.css` + README §Radii):

| Token | px | Elements |
|---|---|---|
| `--r-sm` | 4 | tags / chips — `.ctag`, `.dchip` |
| `--r-md` | 7 | buttons, nav tabs, inputs, `.iconbtn`, `.search`, `.chtoggle`, `.rbtn` |
| `--r-lg` | 9 | stat / step tiles — `.stat`, `.step` |
| `--r-xl` | 10 | match cards — `.m` |
| `--r-2xl` | 12 | cards / panels — `.card`, `.changes`, `.tblwrap`, `.box` |
| `--r-3xl` | 16 | modal & header bottom — `header` (was 20px), modal/popover |
| `--r-pill` | 999 | pills, bars, round selectors, rings — `.pill`, `.prob .track/.fill`, `.lo-bar` |

I'll enumerate the exact `border-radius` sites in Phase 2 and assign each per this table.

## 4c. Typography (per "adopt webfonts" — D2) + flags (per "SVG flags" — D3)

- Add `@import` (or `<link>`) for **Archivo** (600–900) + **IBM Plex Sans** (400–700) + **IBM Plex
  Mono** (400–600) and **flag-icons** CSS. Add `--font-display/--font-sans/--font-mono/--font-emoji`
  tokens. Body → `--font-sans`; numbers (table cells, `.pc`, `.stat .v`, `.dchip`) → mono tabular;
  H1/display → Archivo with `--ls-display`. *(Type-size px stay literal per D5.)*
- `flag()` (line 353) emits `<i class="fl fi fi-XX" aria-hidden>`; add an ISO map (incl. `gb-eng`,
  `gb-sct` for England/Scotland) with the emoji `FLAG` map kept as the no-ISO fallback. Add `.fl.fi`
  helper from `tokens/base.css`. This is the **only** JS edit — `flag()` is presentational (markup
  for a flag glyph); no model/data/logic touched.

---

## 5. Scales the design defines but the app has NOT tokenized → **STOP-and-ask (Phase 1)**

The app has ~316 hardcoded px and no scales. The design defines full scales. Per your plan I will
**not** mass-rewrite px without approval. Proposed scales (from `tokens/spacing.css`, `typography.css`,
`effects.css`):

- **Spacing:** `--sp-1:4 · --sp-2:7 · --sp-3:9 · --sp-4:11 · --sp-5:14 · --sp-6:18 · --sp-7:20 · --sp-8:28`
- **Radius:** `--r-sm:4 · --r-md:7 · --r-lg:9 · --r-xl:10 · --r-2xl:12 · --r-3xl:16 · --r-pill:999`
- **Type scale:** `--fs-2xs:10 · --fs-xs:11.5 · --fs-sm:12.5 · --fs-md:13.5 · --fs-base:15 · --fs-lg:16 · --fs-xl:19 · --fs-2xl:23 · --fs-display:clamp(26px,5.4vw,44px)`
- **Weights / tracking:** `--fw-normal…--fw-black (400–900)`, `--ls-display:-.02em · --ls-tight:-.01em · --ls-label:.12em · --ls-tag:.06em`
- **Fonts:** Archivo (display) · IBM Plex Sans (body) · IBM Plex Mono (numbers) — **webfonts** + flag-icons SVG

---

## 6. Decisions for you (gates before Phase 2)

- **D1 — Canonical source.** Confirm Matchday (`tokens/colors.css`) over the seed: blue header *field*
  (not flattened), cool→hot round arc, vermilion signal. *(My determination from the README.)*
- **D2 — Webfonts.** Adopt Archivo + IBM Plex Sans/Mono via Google Fonts `@import`? This adds external
  font requests to a currently system-font page. Yes = on-brand "quant" type; No = keep system fonts,
  map colors only.
- **D3 — SVG flags vs emoji.** The design mandates **flag-icons SVG** (and a small JS swap in `flag()`).
  ⚠️ Your saved preference is *"emoji flags are fine, don't push SVG."* These conflict. Keep emoji, or
  take the SVG swap? (The swap touches JS, so it's the one place the re-skin would brush the script.)
- **D4 — Movement chips → RESOLVED by design.** The `Badge` component keeps the 5 categories colored,
  retoned to the palette (`flip→signal`, `res→good`, `title→gold`, `route→accent`, `look→qf`). I'll
  apply that (not the seed's de-rainbow). *(My determination — say so if you'd rather neutralize them.)*
- **D5 — Spacing/type/radius tokenization.** Approve tokenizing the ~316 px onto the scales in §5
  (a large mechanical edit), or leave spacing/sizing as-is and remap colors + fonts only?
- **D6 — Live indicator color.** Recolor the Live-odds pulse/indicator from green → vermilion `--signal`
  (design intent), or keep it green?

---

## Phase 3 — Conformance report (applied & verified)

**Edit target:** all changes made in `gen_dashboard.py`'s `TEMPLATE`; `python3 gen_dashboard.py`
regenerates `index.html` + `World_Cup_2026_Predictor.html` (both 128 KB, identical).

**Tokens remapped:** every color var in §1 (light + dark). New tokens added: `--signal`,
`--signal-ink`, `--signal-pulse`, `--hero-ink`, `--hero-mut`, `--on-fill`, `--grad-fill{,-2,-3}`,
`--grad-bd`, `--flag-edge`, `--chip-{flip,res,title,route,look}`, the `--r-*` radius scale, and the
`--font-*` roles. Existing var **names** unchanged (114 call sites intact).

**Bypasses fixed:** all 17 `<style>` color literals routed to tokens. Conformance grep result —
the **only** color literal outside the two token blocks is `#1f4fd6` in `<meta name="theme-color">`
(can't use `var()`; the sanctioned exception). JS region: zero color literals; inline styles are
layout or `var()`-based.

**Decisions resolved:** D1 canonical Matchday ✓ · D2 webfonts (Archivo + IBM Plex Sans/Mono) ✓ ·
D3 flag-icons SVG (emoji fallback kept) ✓ · D4 chips retoned & kept colored ✓ · D5 radius scale
only (spacing/type px untouched) ✓ · D6 live indicator → signal ✓.

**Contrast (WCAG AA, both themes) — all text pairings ≥ 4.5:1:**
- Two regressions the design's bright-in-dark palette introduced were caught and fixed:
  - **`.ctag` movement chips** with theme-flipping fills failed in dark (2.2–3.4) and `flip`
    failed in light (3.4). → Re-tokenized to **fixed** palette hues `--chip-*` (#c0432a / #1f7a4d /
    #9a6313 / #1f4fd6 / #8b46cf), white text **5.0–6.7:1 in both themes**. Still colored & scannable.
  - **`.followtag`** white-on-accent failed in dark (2.69, also pre-existing). → routed to
    `--chip-route` → **6.7:1** both themes (light unchanged).
- One borderline: `--mut`/`--panel2` = 4.44 in light. → `--mut` nudged #6f685b→**#6b6354** → 4.77.
- All `-ink` variants, accent-on-surface, nav tab, and hero-on-gradient pairings pass (5.0–17:1).
- **No pairing ships below AA in either theme.**

**Regression check:** page still fetches `version.json` and the Polymarket Gamma API; bracket,
your-team, teams, groups, method, live-odds all render; light/dark toggle persists across reload
(verified light→light); pre-paint bootstrap, `wc-theme` key, `data-theme` switching, OG/Twitter
meta untouched; no model/data/simulation logic changed. Verified in-browser, desktop + mobile.

## Added in this rebuild (beyond the re-skin, per request)

- **Bracket Tree tab** — a new mirrored, connected knockout tree (vanilla JS + SVG, no React),
  driven by the real `DATA.matches` / `ROUND_ORDER` bracket structure: per-round colored stripes,
  SVG connectors, a vermilion projected-champion trophy, projected-advancer emphasis, followed-team
  path highlighting, tap-a-box-to-follow, scales to fit (pannable on mobile).
- **Removed the date/bracket order toggle** — the Bracket tab is now fixed to date (kickoff) order;
  the slot-structure view lives in the new Bracket Tree tab. Toggle HTML, CSS, JS, and the
  `wc-sort` localStorage key all removed.
