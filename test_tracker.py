"""Student-protest tracker. Tests run before each daily update. Usage: python test_tracker.py"""
import numpy as np, pandas as pd
import build, update_from_files as u

def series(seed=0):
    """Six years, four countries: QUIET (steady), WAVE (steady, then a wave in the last week), BLIP (steady, then four reports on one day), RARE (two reports a year)."""
    rng = np.random.default_rng(seed); days = pd.date_range('2020-01-01', '2025-12-31'); T = len(days)
    N = pd.DataFrame({c: rng.poisson(0.6, T) for c in ('QUIET', 'WAVE', 'BLIP')}, index=days).astype(float); N['RARE'] = 0.0; N.loc[N.index[::180], 'RARE'] = 1
    E = pd.DataFrame(2000.0, index=days, columns=N.columns)
    N.iloc[-7:, N.columns.get_loc('WAVE')] = 40; N.iloc[-7:, N.columns.get_loc('BLIP')] = 0; N.iloc[-1, N.columns.get_loc('BLIP')] = 4
    return N, E

def test_rule():
    N, E = series(); B = build.flags(N, E, first='2025-01-01'); tier, raw = B['tier'].iloc[-1], B['raw'].iloc[-1]
    assert tier['WAVE'] == 3 and B['pct']['WAVE'].iloc[-1] > 99, 'a wave must be exceptional'
    assert tier['QUIET'] <= 1, 'a steady country must not be flagged high'
    assert tier['BLIP'] == 0, 'four reports on one day must not raise a flag'
    assert tier['RARE'] == -1, 'a country with two reports a year must not be ranked'
    quiet = B['tier']['QUIET']; assert (quiet >= 2).mean() < 0.05, 'a steady country is far above usual on few days'
    assert build.run_length(B['tier'] >= 1)['WAVE'] >= 5, 'the wave has lasted several days'

def test_guard_holds_back():
    N, E = series(1); N['BLIP'] = 0.0; N.loc[N.index[::20], 'BLIP'] = 1; N.iloc[-7:, N.columns.get_loc('BLIP')] = 0; N.iloc[-1, N.columns.get_loc('BLIP')] = 4          # usually one report every 20 days; four on the last day
    B = build.flags(N, E, first='2025-06-01'); assert B['raw']['BLIP'].iloc[-1] >= 2 and B['tier']['BLIP'].iloc[-1] == 0, 'a jump of four reports on one day is high before the guards and held back after'

def test_no_look_ahead():
    N, E = series(2); B1 = build.flags(N, E, first='2025-01-01'); N2 = N.copy(); N2.iloc[-30:] = 99; B2 = build.flags(N2, E, first='2025-01-01')
    assert B1['tier'].iloc[:-30].equals(B2['tier'].iloc[:-30]) and np.allclose(B1['pct'].iloc[:-30], B2['pct'].iloc[:-30]), 'a day must be judged only with the days before it'

def test_line():
    """One made-up line of a GDELT export file (61 tab-separated fields) is counted as the code intends."""
    from collections import defaultdict
    def line(**k):
        r = [''] * 61; r[1] = '20261011'; r[6] = 'STUDENT'; r[12] = 'EDU'; r[22] = 'GOV'; r[26] = '141'; r[28] = '14'; r[33] = '3'; r[53] = 'FR'; r[60] = 'https://example.org/a'
        for i, v in k.items(): r[int(i[1:])] = v
        return r
    out = defaultdict(lambda: [0, 0, 0, 0, 0]); reports = []
    assert u.count(line(), out, reports) and out[(20261011, 'FR')] == [1, 3, 1, 1, 1] and reports == [(20261011, 'FR', '141', 'GOV', 3, 'https://example.org/a', 'STUDENT')], 'a protest by students is an event, a protest, an education protest and a report'
    u.count(line(f6='FRANCE'), out, reports); assert out[(20261011, 'FR')] == [2, 6, 2, 2, 1] and len(reports) == 1, 'an education actor named only by a country is not a report'
    u.count(line(f6='PROFESSOR', f12=''), out, reports); assert out[(20261011, 'FR')] == [3, 9, 3, 2, 1], 'a protest by another actor is only a protest'
    u.count(line(f28='04'), out, reports); assert out[(20261011, 'FR')] == [4, 12, 3, 2, 1], 'an event that is not a protest is only an event'
    assert not u.count(line(f1='20260931'), out, reports) and not u.count(line(f53=''), out, reports) and not u.count(line()[:40], out, reports) and len(out) == 1, 'an impossible date, a line without a country and a short line are left out'
    assert u.next_day(20261231) == 20270101 and u.next_day(20280228) == 20280229 and u.COLS[-1] == 'student_protests'

def test_places():
    """The places an article names, read from a made-up knowledge-graph file, and the guard that sets aside a wave reported from elsewhere."""
    import io, zipfile
    rec = lambda url, locs: '\t'.join(['id', '20261011120000', '1', 'site', url, '', '', '', '', '', locs] + [''] * 16)
    text = '\n'.join([rec('https://example.org/a', '4#Paris, France#FR#FR00#1#48.8#2.3#-1#10;4#Lyon, France#FR#FR00#2#45.7#4.8#-2#90;1#Belgium#BE#BE##50.8#4.3#BE#200'), rec('https://example.org/b', ''), 'short line'])
    buf = io.BytesIO(); z = zipfile.ZipFile(buf, 'w'); z.writestr('x.gkg.csv', text); z.close()
    found = u.places(buf.getvalue(), {'https://example.org/a', 'https://example.org/b', 'https://example.org/c'})
    assert found == {'https://example.org/a': {'FR': 2, 'BE': 1}, 'https://example.org/b': {}}, 'two mentions of places in France, one in Belgium; an article without places; an article not in the file'
    r = u.with_places([(20261011, 'BE', '141', '', 1, 'https://example.org/a', 'STUDENT'), (20261011, 'FR', '141', '', 1, 'https://example.org/a', 'STUDENT'), (20261011, 'FR', '141', '', 1, 'https://example.org/c', 'STUDENT')], found)
    assert [x[7:] for x in r] == [(0.333, 'FR'), (0.667, 'FR'), ('', '')], 'the share of the places in the country of the report, and nothing when the article is unknown'
    assert u.places(b'not a zip file', {'https://example.org/a'}) == {}
    N, E = series(3); l7 = pd.DataFrame(np.nan, index=N.index, columns=N.columns); d7 = l7.copy(); l7.iloc[-10:] = 280.0; d7.iloc[-10:] = 7.0; l7.iloc[-10:, N.columns.get_loc('WAVE')] = 2.0
    B = build.flags(N, E, first='2025-06-01', places=(l7, d7)); free = build.flags(N, E, first='2025-06-01')
    assert free['tier']['WAVE'].iloc[-1] == 3 and B['tier']['WAVE'].iloc[-1] == 0 and B['moved']['WAVE'].iloc[-1] == 1, 'a wave whose articles are about other places is held back'
    assert B['tier'].iloc[:-10].equals(free['tier'].iloc[:-10]), 'where the places are not known, nothing changes'

def test_missing_files():
    """The daily update when GDELT's files are incomplete, with made-up days in a temporary folder and no download."""
    import datetime, json, os, tempfile
    today = datetime.datetime.now(datetime.timezone.utc).date(); day = lambda k: int((today - datetime.timedelta(days=k)).strftime('%Y%m%d')); iso = lambda k: (today - datetime.timedelta(days=k)).strftime('%Y-%m-%d')
    keep = {k: getattr(u, k) for k in ('DATA', 'ADDED', 'REPORTS', 'COVERAGE', 'BASE', 'DAILY', 'BASE_LAST_ADDED', 'BASE_RECENT_FROM', 'read_day')}
    with tempfile.TemporaryDirectory() as d:
        try:
            u.DATA = d; u.ADDED = os.path.join(d, 'added'); os.makedirs(u.ADDED); u.REPORTS = os.path.join(d, 'reports'); u.COVERAGE = os.path.join(u.ADDED, 'coverage.csv'); u.BASE = os.path.join(d, 'base.csv.gz'); u.DAILY = os.path.join(d, 'daily.csv.gz')
            u.BASE_LAST_ADDED = day(6); u.BASE_RECENT_FROM = day(20); pd.DataFrame([(day(6), 'FR', 10, 20, 1, 1, 1)], columns=u.COLS).to_csv(u.BASE, index=False)
            files = {day(5): 100, day(4): 192, day(3): 192, day(2): 100, day(1): 192}                # files GDELT has for each day of publication
            u.read_day = lambda k: ({(int(k), 'FR'): [10, 20, 1, 1, 1], (day(30), 'FR'): [5, 5, 1, 1, 1]}, files[int(k)], [(int(k), 'FR', '141', '', 2, 'https://example.org/a', 'STUDENT', 0.8, 'FR')])          # each day also brings an event dated a month ago
            u.main(); info = json.load(open(os.path.join(d, 'pull_info.json')))
            assert info['last_complete_day'] == str(day(3)), 'the series must stop before a recent day with files missing'
            assert not os.path.exists(os.path.join(u.ADDED, f'{day(1)}.csv')), 'nothing is stored after a day that is still awaited'
            assert info['incomplete_days'] == {iso(5): 100}, 'an old day with files missing is stored and recorded'
            files[day(2)] = 192; files[day(3)] = 150; u.main(); info = json.load(open(os.path.join(d, 'pull_info.json'))); cov = pd.read_csv(u.COVERAGE)
            assert info['last_complete_day'] == str(day(1)) and int(cov[cov.day == day(3)].files.iloc[0]) == 192, 'a stored day is kept when fewer files answer at the second reading'
            D = pd.read_csv(u.DAILY); old = D[D.day == day(30)].iloc[0]; assert len(D) == 7 and D.student_protests.sum() == 11, 'one row for the base, one for each stored day and one for the old date'
            assert old.events == 20 and old.student_protests == 5, 'on the first day after the base, an event dated before BASE_RECENT_FROM adds its report and nothing else'
        finally:
            for k, v in keep.items(): setattr(u, k, v)

def test_page():
    """The page: its script parses (checked with node when node is installed) and both languages have the same texts."""
    import os, re, shutil, subprocess, tempfile
    s = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page', 'index.html'), encoding='utf-8').read(); js = s[s.index('<script>') + 8:s.rindex('</script>')]
    keys = lambda b: set(re.findall(r'^\s*"([^"]+)": ', b, re.M)); a, b = js.index('  en: {'), js.index('  fr: {'); en, fr = js[a:b], js[b:js.index('\n};', b)]
    assert len(keys(en)) > 50 and keys(en) == keys(fr), 'texts present in one language only: ' + ', '.join(sorted(keys(en) ^ keys(fr)))
    node = shutil.which('node') or (r'C:\Program Files\nodejs\node.exe' if os.path.exists(r'C:\Program Files\nodejs\node.exe') else None)
    if node:
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, 'page.js'); open(f, 'w', encoding='utf-8').write(js); r = subprocess.run([node, '--check', f], capture_output=True, text=True)
            assert r.returncode == 0, 'the script of the page does not parse: ' + r.stderr[-300:]

if __name__ == '__main__':
    for f in (test_rule, test_guard_holds_back, test_no_look_ahead, test_line, test_places, test_page, test_missing_files): f(); print('passed:', f.__name__, flush=True)
