"""Student-protest tracker. Daily update: downloads the files the GDELT Project publishes each day and counts the reports by day and country. Usage: python update_from_files.py"""
import csv, datetime, functools, io, json, os, re, sys, time, urllib.error, urllib.request, zipfile
from collections import defaultdict
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, 'data'); ADDED = os.path.join(DATA, 'added'); os.makedirs(ADDED, exist_ok=True)
BASE, DAILY = os.path.join(DATA, 'base.csv.gz'), os.path.join(DATA, 'daily.csv.gz'); REPORTS = os.path.join(DATA, 'reports'); COVERAGE = os.path.join(ADDED, 'coverage.csv')
BASE_FIRST = 20170101
BASE_LAST_ADDED = 20261010
BASE_RECENT_FROM = 20261001
URL = 'http://data.gdeltproject.org/gdeltv2/{stamp}.{kind}.CSV.zip'; KINDS = ('export', 'translation.export')
GKG_URL = 'http://data.gdeltproject.org/gdeltv2/{stamp}.{kind}.csv.zip'; GKG_KIND = {'export': 'gkg', 'translation.export': 'translation.gkg'}
REPORT_COLS = ['day', 'fips', 'code', 'target', 'articles', 'url', 'actor', 'own_share', 'main']
STUDENT = re.compile(r'STUDENT|PUPIL|SCHOOL|UNIVERSIT|LYCEE|LYCEEN|UNDERGRAD|CAMPUS'); MIN_FILES = 180; STALE_DAYS = 2; GRACE_DAYS = 3
COLS = ['day', 'fips', 'events', 'articles', 'protests', 'education_protests', 'student_protests']
csv.field_size_limit(10 ** 9)
next_day = lambda k: int((datetime.datetime.strptime(str(k), '%Y%m%d') + datetime.timedelta(days=1)).strftime('%Y%m%d'))

def fetch(url, tries=3):
    for k in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'student-protest-tracker/1.0'}), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
        except Exception: pass
        time.sleep(2 + 3 * k)
    return None

@functools.lru_cache(maxsize=None)
def real_day(s):
    try: datetime.datetime.strptime(s, '%Y%m%d'); return len(s) == 8
    except ValueError: return False

def count(r, out, reports):
    if len(r) < 61 or not r[53] or not real_day(r[1]): return False
    k = out[(int(r[1]), r[53])]; n = int(r[33]) if r[33].isdigit() else 0; k[0] += 1; k[1] += n
    if r[28] == '14':
        k[2] += 1; named = bool(STUDENT.search(r[6]))
        if named or 'EDU' in (r[12], r[13], r[14]): k[3] += 1
        if named: k[4] += 1; reports.append((int(r[1]), r[53], r[26], r[22], n, r[60], r[6]))
    return True

def places(blob, urls):
    out = {}; want = {u.encode('utf-8', 'replace') for u in urls}
    try: z = zipfile.ZipFile(io.BytesIO(blob)); raw = z.read(z.namelist()[0])
    except Exception: return out
    for line in raw.split(b'\n'):
        r = line.split(b'\t')
        if len(r) > 10 and r[4] in want:
            c = {}
            for loc in r[10].split(b';'):
                p = loc.split(b'#')
                if len(p) > 2 and p[2]: k = p[2].decode('ascii', 'replace'); c[k] = c.get(k, 0) + 1
            out[r[4].decode('utf-8', 'replace')] = c
    return out

def with_places(new, found):
    done = []
    for r in new:
        c = found.get(r[5]) or {}; n = sum(c.values()); done.append(r + ((round(c.get(r[1], 0) / n, 3), max(c, key=c.get)) if n else ('', '')))
    return done

def read_day(day):
    out = defaultdict(lambda: [0, 0, 0, 0, 0]); files = 0; reports = []
    for q in range(96):
        stamp = f'{day}{q // 4:02d}{15 * (q % 4):02d}00'
        for kind in KINDS:
            blob = fetch(URL.format(stamp=stamp, kind=kind))
            if blob is None: continue
            try: z = zipfile.ZipFile(io.BytesIO(blob)); text = z.read(z.namelist()[0]).decode('utf-8', 'replace')
            except Exception: continue
            files += 1; n0 = len(reports)
            for r in csv.reader(io.StringIO(text), delimiter='\t', quoting=csv.QUOTE_NONE): count(r, out, reports)
            if len(reports) > n0:
                blob = fetch(GKG_URL.format(stamp=stamp, kind=GKG_KIND[kind])); reports[n0:] = with_places(reports[n0:], places(blob, {r[5] for r in reports[n0:]}) if blob else {})
    return out, files, reports

def store(day, partial=False):
    counts, files, reports = read_day(day)
    cov = pd.read_csv(COVERAGE, dtype={'day': str}) if os.path.exists(COVERAGE) else pd.DataFrame(columns=['day', 'files'])
    before = int(cov[cov.day == str(day)].files.max()) if (cov.day == str(day)).any() and os.path.exists(os.path.join(ADDED, f'{day}.csv')) else None
    if before is not None and files < before: print(f'{day}: {files} files now, {before} when stored: kept as stored', flush=True); return before
    if files < MIN_FILES and not partial and before is None: print(f'{day}: {files} of 192 files, not stored', flush=True); return None
    os.makedirs(REPORTS, exist_ok=True); pd.DataFrame(reports, columns=REPORT_COLS).sort_values(['day', 'fips']).to_csv(os.path.join(REPORTS, f'{day}.csv'), index=False)
    first = int(day) == next_day(BASE_LAST_ADDED)
    rows = [(d, f, *(v if not (first and d < BASE_RECENT_FROM) else [0, 0, 0, 0, v[4]])) for (d, f), v in counts.items() if d >= BASE_FIRST]
    rows = [r for r in rows if any(r[2:])]
    pd.DataFrame(rows, columns=COLS).sort_values(['day', 'fips']).to_csv(os.path.join(ADDED, f'{day}.csv'), index=False)
    if int(day) > BASE_LAST_ADDED: pd.concat([cov[cov.day != str(day)], pd.DataFrame([dict(day=str(day), files=files)])]).sort_values('day').to_csv(COVERAGE, index=False)
    print(f'{day}: {files} files, {len(rows)} rows, {len(reports)} reports', flush=True); return files

def stored_days():
    have = {int(f[:8]) for f in os.listdir(ADDED) if f[:8].isdigit() and f.endswith('.csv') and int(f[:8]) > BASE_LAST_ADDED}; run = []; k = next_day(BASE_LAST_ADDED)
    while k in have: run.append(k); k = next_day(k)
    return run

def rebuild():
    run = stored_days(); kw = dict(keep_default_na=False, na_values=[''])
    parts = [pd.read_csv(BASE, **kw)] + [pd.read_csv(os.path.join(ADDED, f'{k}.csv'), **kw) for k in run]
    D = pd.concat(parts, ignore_index=True).groupby(['day', 'fips'], as_index=False)[COLS[2:]].sum().sort_values(['day', 'fips']); D.to_csv(DAILY, index=False)
    last = run[-1] if run else BASE_LAST_ADDED; cov = pd.read_csv(COVERAGE, dtype={'day': str}) if os.path.exists(COVERAGE) else pd.DataFrame(columns=['day', 'files'])
    gaps = {f'{d[:4]}-{d[4:6]}-{d[6:]}': int(n) for d, n in zip(cov.day, cov.files) if int(n) < MIN_FILES and int(d) in run}
    json.dump(dict(pulled_at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), last_complete_day=str(last), incomplete_days=gaps, source='GDELT 2.0 event files (data.gdeltproject.org/gdeltv2)'), open(os.path.join(DATA, 'pull_info.json'), 'w'), indent=1)
    print(f'daily series rebuilt: {len(D):,} rows, last complete day of publication {last}' + (f'; days with files missing: {gaps}' if gaps else ''), flush=True)

def main():
    args = sys.argv[1:]; today = datetime.datetime.now(datetime.timezone.utc).date()
    if '--day' in args: store(args[args.index('--day') + 1], partial=True); rebuild(); return
    have = stored_days(); k = next_day(BASE_LAST_ADDED); limit = int(today.strftime('%Y%m%d'))
    while k < limit:
        age = (today - datetime.datetime.strptime(str(k), '%Y%m%d').date()).days
        if k not in have:
            if store(str(k), partial=age > GRACE_DAYS) is None: print(f'stopping at {k}: it will be tried again at the next run', flush=True); break
        elif k in have[-STALE_DAYS:]: store(str(k))
        k = next_day(k)
    rebuild()

if __name__ == '__main__': main()
