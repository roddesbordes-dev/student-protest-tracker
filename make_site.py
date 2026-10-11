"""Student-protest tracker. Wraps the page and its tables into the static site in docs/. Usage: python make_site.py"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); DOCS = os.path.join(HERE, 'docs'); os.makedirs(os.path.join(DOCS, 'data'), exist_ok=True)
TABLES = ['latest', 'recent', 'monthly', 'world', 'info', 'forms', 'articles']
FILE = {}

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Student protest tracker</title>
<meta name="description" content="Daily tracker of news reports of student protest in every country, from GDELT, each country compared with its own past. In English and French.">
<style>
:root {
  --color-bg: #f6f7f9; --color-panel: #ffffff; --color-fg: #16202b; --color-fg-muted: #5a6673; --color-border-line: #d9dee4;
  --color-ok: #00735c; --color-warn: #a35c00; --color-bad: #c14a00;
  --series-1: #0072b2;
  --cds-chart-muted: #9aa5b1; --cds-chart-grid: #e6e9ed; --cds-chart-axis: #9aa5b1; --cds-chart-reference: #5a6673; --cds-chart-status-critical: #c14a00;
  --cds-surface-popover: #ffffff; --cds-border: #c9d0d8; --cds-shadow-popover: 0 4px 14px rgba(22, 32, 43, .16);
  --cds-radius: 8px; --cds-gap-xs: .25rem; --cds-gap-sm: .5rem; --cds-gap-md: 1rem; --cds-gap-lg: 1.5rem; --cds-gap-xl: 2.25rem;
  --cds-pad-xs: .3rem; --cds-pad-sm: .55rem; --cds-pad-md: .9rem; --cds-pad-lg: 1.25rem; --cds-pad-xl: 2rem;
  --cds-font-size-caption: .8125rem; --cds-font-size-body: .9375rem; --cds-font-size-heading: 1.0625rem; --cds-font-size-title: 2rem; --cds-font-weight-medium: 600;
  --cds-dur-slow: .3s; --cds-ease-out: ease-out;
  --font-anthropic-sans: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
  --font-anthropic-serif: Georgia, "Iowan Old Style", "Palatino Linotype", "Times New Roman", serif;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root {
  --color-bg: #12171d; --color-panel: #1a212a; --color-fg: #e8edf2; --color-fg-muted: #9eabb8; --color-border-line: #2e3945;
  --color-ok: #4fc9a8; --color-warn: #e69f00; --color-bad: #ff8a4c;
  --series-1: #56b4e9;
  --cds-chart-muted: #6c7a89; --cds-chart-grid: #263039; --cds-chart-axis: #6c7a89; --cds-chart-reference: #9eabb8; --cds-chart-status-critical: #ff8a4c;
  --cds-surface-popover: #232c37; --cds-border: #3a4755; --cds-shadow-popover: 0 4px 14px rgba(0, 0, 0, .5);
  color-scheme: dark;
} }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); font-size: 15px; }
#dash-root { padding-inline: var(--dash-gutter, 16px); }
.dash-skeleton { background: var(--cds-chart-grid); border-radius: var(--cds-radius); color: transparent !important; }
</style>
</head>
<body>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>
window.TRACKER_PUBLIC = __PUBLIC__;      // tells the page it runs on the public site: it then shows its footer and sets the document language
// The interface the page expects: tables read from CSV files beside the page, and values computed from them.
window.dash = (() => {
  const TABLES = __TABLES__, sets = {}, calcs = {}, subs = [];
  const fire = () => subs.forEach((f) => { try { f(); } catch (e) { console.error(e); } });
  const data = (id) => {
    if (calcs[id]) {
      const ins = calcs[id].inputs.map(data);
      if (ins.some((i) => i.status === 'error')) return {status: 'error', data: [], message: 'an input failed to load'};
      if (!ins.every((i) => i.status === 'ok')) return {status: 'loading', data: []};
      try { return {status: 'ok', data: calcs[id].fn(...ins.map((i) => i.data))}; } catch (e) { return {status: 'error', data: [], message: String(e)}; }
    }
    return sets[id] || {status: 'missing', data: []};
  };
  for (const id of TABLES) {
    sets[id] = {status: 'loading', data: [], columns: []};
    fetch(`data/${id}.csv`, {cache: 'no-cache'}).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text(); })
      .then((t) => { const rows = d3.csvParse(t); sets[id] = {status: 'ok', data: rows, columns: rows.columns}; fire(); })
      .catch((e) => { sets[id] = {status: 'error', data: [], columns: [], message: String(e)}; fire(); });
  }
  let timer, width = window.innerWidth; window.addEventListener('resize', () => { if (window.innerWidth === width) return; width = window.innerWidth; clearTimeout(timer); timer = setTimeout(fire, 150); });      // redraw the charts when the width changes (not when a phone's address bar hides)
  return {data, onData: (fn) => { subs.push(fn); fn(); }, calc: (id, c) => { calcs[id] = c; }, colors: ['var(--series-1)'], refresh() {}, params: () => ({}), setParams() {}, resetParams() {}, setLink() {}};
})();
</script>
<div id="dash-root">
"""
FOOT = """
</div>
</body>
</html>
"""
page = open(os.path.join(HERE, 'page', 'index.html'), encoding='utf-8').read()
import json
html = HEAD.replace('__TABLES__', json.dumps(TABLES)).replace('__PUBLIC__', json.dumps(dict(repo='', full=False))) + page + FOOT
open(os.path.join(DOCS, 'index.html'), 'w', encoding='utf-8', newline='\n').write(html)
for f in os.listdir(os.path.join(DOCS, 'data')):          # copies left by an earlier build of tables this build does not publish
    if f.endswith('.csv') and f[:-4] not in TABLES: os.remove(os.path.join(DOCS, 'data', f))
for t in TABLES: shutil.copyfile(os.path.join(OUT, FILE.get(t, t) + '.csv'), os.path.join(DOCS, 'data', f'{t}.csv'))
open(os.path.join(DOCS, '.nojekyll'), 'w').close()
print('site written to docs/:', round(len(html) / 1024), 'KB page,', len(TABLES), 'tables,', round(sum(os.path.getsize(os.path.join(DOCS, 'data', f'{t}.csv')) for t in TABLES) / 1024), 'KB of data')
