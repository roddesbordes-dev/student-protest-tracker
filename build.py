"""Student-protest tracker. Builds the tables the page shows from the daily counts. Usage: python build.py"""
import datetime, json, os, sys
import numpy as np, pandas as pd
from countries import NAME, REGION, NAME_FR, REGION_FR

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, 'data'); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
CODE = ['usual', 'elevated', 'high', 'exceptional']; CUTS = (80, 95, 99); MIN_REPORTS = 5; MIN_ACTIVE_DAYS = 3; MIN_PER_MONTH = 1.0; MAX_AGE_DAYS = 4
SEASON = 30; REF_DAYS = 3 * 365; REF_GAP = 30; HISTORY_FROM = '2020-02-15'

def load():
    D = pd.read_csv(os.path.join(DATA, 'daily.csv.gz'), keep_default_na=False, na_values=['']); D = D[D.fips.isin(NAME)]; D['day'] = pd.to_datetime(D.day.astype(str), format='%Y%m%d', errors='coerce'); D = D[D.day.notna()]
    info = json.load(open(os.path.join(DATA, 'pull_info.json'))); last = pd.Timestamp(info['last_complete_day'])
    present = set(D.day.unique()); days = pd.date_range(D.day.min(), last); wide = lambda c: D.pivot(index='day', columns='fips', values=c).reindex(days).fillna(0)
    return wide('student_protests'), wide('events'), info, [d for d in days[-60:] if d not in present]

def flags(N, E, first=HISTORY_FROM, places=None):
    idx, cols = N.index, N.columns; n7 = N.rolling(7).sum().fillna(0).values; e7 = E.rolling(7).sum().fillna(0).values; a7 = (N > 0).rolling(7).sum().fillna(0).values
    with np.errstate(invalid='ignore', divide='ignore'): S = np.where(e7 > 0, 1000 * n7 / e7, np.nan)
    Nv = N.values; doy = idx.dayofyear.values; T, C = Nv.shape; start = min(T - 1, max(REF_GAP + 400, int(idx.searchsorted(pd.Timestamp(first)))))
    out = {k: np.full((T, C), np.nan) for k in ('tier', 'raw', 'moved', 'pct', 'pcts', 'usual', 'per_week')}; seen = ~np.isnan(S)
    l7, d7 = (places[0].reindex(index=idx, columns=cols).values, places[1].reindex(index=idx, columns=cols).values) if places is not None else (np.full((T, C), np.nan),) * 2
    for i in range(start, T):
        lo, hi = max(0, i - REF_GAP - REF_DAYS), i - REF_GAP; rows = slice(lo, hi + 1); ref = S[rows]; ok = seen[rows]; now = S[i]
        with np.errstate(invalid='ignore'): pct = 100 * ((ref < now) & ok).sum(0) / np.maximum(ok.sum(0), 1)
        j = max(0, i - 300); gap = np.abs(doy[:j] - doy[i]); rs = np.flatnonzero(np.minimum(gap, 366 - gap) <= SEASON); sea = S[rs]; oks = seen[rs]
        with np.errstate(invalid='ignore'): pcts = np.where(oks.sum(0) > 100, 100 * ((sea < now) & oks).sum(0) / np.maximum(oks.sum(0), 1), pct)
        per_week = Nv[rows].sum(0) / (REF_DAYS / 7); m = np.minimum(pct, pcts); raw = sum((m >= c).astype(int) for c in CUTS)
        enough = (n7[i] >= MIN_REPORTS) & (a7[i] >= MIN_ACTIVE_DAYS); tracked = per_week * 4.35 >= MIN_PER_MONTH
        with np.errstate(all='ignore'): out['usual'][i] = np.where(ok.any(0), np.nanmedian(np.where(ok, ref, np.nan), axis=0), np.nan)
        with np.errstate(invalid='ignore'): here = np.isnan(l7[i]) | ((l7[i] >= MIN_REPORTS) & (d7[i] >= MIN_ACTIVE_DAYS))
        out['tier'][i] = np.where(tracked, raw * enough * here, -1); out['raw'][i] = raw; out['moved'][i] = (raw > 0) & enough & ~here; out['pct'][i] = pct; out['pcts'][i] = pcts; out['per_week'][i] = per_week
    frame = lambda X: pd.DataFrame(X, index=idx, columns=cols)
    return dict({k: frame(v).iloc[start:] for k, v in out.items()}, n7=frame(n7), a7=frame(a7), S7=frame(S))

def run_length(above):
    a = above.values; run = np.zeros(a.shape[1], int); alive = np.ones(a.shape[1], bool)
    for k in range(len(a) - 1, -1, -1): alive &= a[k]; run += alive
    return pd.Series(run, index=above.columns)

def main():
    N, E, info, missing = load(); last = N.index.max(); today = pd.Timestamp(datetime.datetime.now(datetime.timezone.utc).date())
    import describe; R = describe.load(last); l7, d7 = describe.located(R, N.index, N.columns)
    B = flags(N, E, places=(l7, d7)); n7, a7, S7 = B['n7'], B['a7'], B['S7']; e7 = E.rolling(7).sum().fillna(0)
    fatal = []; world7 = n7.sum(axis=1); events7 = e7.sum(axis=1); typical = events7.iloc[-400:-30].median()
    if (today - last).days > MAX_AGE_DAYS: fatal.append(f'the series ends on {last.date()}, more than {MAX_AGE_DAYS} days ago')
    if missing: fatal.append(f'{len(missing)} days without any data in the last 60: {[d.strftime("%m-%d") for d in missing[:5]]}')
    if not 0.25 * typical <= events7.iloc[-1] <= 3 * typical: fatal.append(f'{int(events7.iloc[-1]):,} events worldwide in the last seven days, against a typical {int(typical):,}')
    if fatal and '--force' not in sys.argv: raise SystemExit('build stopped, nothing written: ' + '; '.join(fatal))
    recent_gaps = {d: n for d, n in (info.get('incomplete_days') or {}).items() if (last - pd.Timestamp(d)).days < 45}

    per_week = B['per_week'].iloc[-1]
    tier, raw, moved = B['tier'].iloc[-1], B['raw'].iloc[-1], B['moved'].iloc[-1]; tracked = [c for c in N.columns if tier[c] >= 0]; run = run_length(B['tier'] >= 1); year = (B['tier'].iloc[-365:] >= 2).sum(); rows = []
    for c in N.columns:
        base = dict(country=NAME[c], country_fr=NAME_FR[c], region=REGION[c], region_fr=REGION_FR[REGION[c]], tracked=int(c in tracked), reports=int(n7[c].iloc[-1]), active_days=int(a7[c].iloc[-1]), reports_per_week=round(per_week[c], 1),
                    data='rich' if per_week[c] >= 3 else 'moderate' if per_week[c] >= 1 else 'thin')
        if c not in tracked:
            rows.append(dict(base, data='too thin', share=np.nan, usual=np.nan, percentile=np.nan, percentile_season=np.nan, tier='not ranked', signal='', located=np.nan, run_days=np.nan, far_days_year=np.nan)); continue
        now = S7[c].iloc[-1]; usual = B['usual'][c].iloc[-1]
        rows.append(dict(base, share=round(now, 3), usual=round(usual, 3), percentile=round(B['pct'][c].iloc[-1], 1), percentile_season=round(B['pcts'][c].iloc[-1], 1), tier=CODE[int(tier[c])],
                         signal='elsewhere' if moved[c] == 1 else 'held back' if raw[c] > 0 and tier[c] == 0 else '', located=int(l7[c].iloc[-1]) if pd.notna(l7[c].iloc[-1]) else np.nan, run_days=int(run[c]), far_days_year=int(year[c])))
    nf, na, urls = describe.main(last, R); print(f'forms: {nf} rows; articles: {na} rows')
    press = pd.read_csv(os.path.join(DATA, 'press.csv'), keep_default_na=False, na_values=['']).set_index('country').press if os.path.exists(os.path.join(DATA, 'press.csv')) else pd.Series(dtype=str)
    order = {t: i for i, t in enumerate(CODE[::-1])}; L = pd.DataFrame(rows); L['press'] = L.country.map(press).fillna(''); L['articles'] = L.country.map(urls).fillna(0).astype(int)
    L['o'] = L.tier.map(order).fillna(9); L['p'] = L[['percentile', 'percentile_season']].min(axis=1)
    L = L.sort_values(['o', 'p', 'reports'], ascending=[True, False, False]).drop(columns=['o', 'p']); L.to_csv(os.path.join(OUT, 'latest.csv'), index=False)
    names = {c: NAME[c] for c in tracked}; tail = slice(last - pd.Timedelta(days=179), last)
    long = lambda X, v: X[tracked].loc[tail].rename(columns=names).rename_axis('day').reset_index().melt('day', var_name='country', value_name=v)
    R = long(S7.round(3), 'share').merge(long(n7.astype(int), 'reports'), on=['day', 'country']).merge(long(N.astype(int), 'reports_day'), on=['day', 'country']); R['day'] = R.day.dt.strftime('%Y-%m-%d'); R.to_csv(os.path.join(OUT, 'recent.csv'), index=False)
    Nm, Em = N[tracked].resample('MS').sum(), E[tracked].resample('MS').sum(); lm = lambda X, v: X.rename(columns=names).rename_axis('month').reset_index().melt('month', var_name='country', value_name=v)
    M = lm((1000 * Nm / Em.where(Em > 0)).round(3), 'share').merge(lm(Nm.astype(int), 'reports'), on=['month', 'country']).dropna(); M['month'] = M.month.dt.strftime('%Y-%m-%d'); M.to_csv(os.path.join(OUT, 'monthly.csv'), index=False)
    W = pd.DataFrame({'world': (1000 * n7.sum(axis=1) / e7.sum(axis=1)).round(3)}).loc[tail].rename_axis('day').reset_index(); W['day'] = W.day.dt.strftime('%Y-%m-%d')
    W.to_csv(os.path.join(OUT, 'world.csv'), index=False)
    T0 = B['tier'].where(~((B['moved'] == 1) & (B['tier'] >= 0)), B['raw'])
    days_ranked = (T0 >= 0).values.sum(); at = {k: round(100 * float((T0 == k).values.sum() / days_ranked), 1) for k in (1, 2, 3)}
    out = dict(last_day=last.strftime('%Y-%m-%d'), pulled_at=info['pulled_at'], reports_last_7_days=int(world7.iloc[-1]),
               checks='passed' if not fatal else '; '.join(fatal), incomplete=' '.join(f'{d}:{n}' for d, n in sorted(recent_gaps.items())),
               at_elevated=at[1], at_high=at[2], at_exceptional=at[3])
    pd.DataFrame([out]).to_csv(os.path.join(OUT, 'info.csv'), index=False)
    print(json.dumps(out))

if __name__ == '__main__': main()
