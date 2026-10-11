"""Student-protest tracker. Forms of protest and articles by country, for the page. Called by build.py."""
import os, re, urllib.parse
import pandas as pd
from countries import NAME
from update_from_files import BASE_LAST_ADDED

HERE = os.path.dirname(os.path.abspath(__file__)); REP = os.path.join(HERE, 'data', 'reports'); OUT = os.path.join(HERE, 'out')
FORM = {'140': 'Demonstration', '141': 'Demonstration', '142': 'Hunger strike', '143': 'Strike or boycott', '144': 'Blockade or occupation', '145': 'Violent protest'}
TARGET = {'GOV': 'Government', 'COP': 'Police', 'EDU': 'Schools and universities', 'LEG': 'Parliament', 'JUD': 'Courts', 'MIL': 'Military', 'OPP': 'Opposition', 'LAB': 'Labour', 'BUS': 'Business', 'CVL': 'Civilians'}
PLACES_FROM = pd.Timestamp('2026-09-27'); MAJORITY = 0.5          # the places each article names are known from this day on; a report is 'elsewhere' when under half of them are in its country
ACTOR = lambda a: 'Students or pupils' if re.search(r'STUDENT|PUPIL|LYCEEN|UNDERGRAD', a) else 'University or campus' if re.search(r'UNIVERSIT|CAMPUS', a) else 'School'

def title_of(url):
    """A readable title from the address of an article: its longest hyphenated part, without numbers and file endings."""
    try: u = urllib.parse.urlparse(url); parts = [urllib.parse.unquote(p) for p in u.path.split('/') if p]
    except Exception: return ''
    best = max(parts, key=lambda p: len(re.findall(r'[A-Za-zÀ-ɏͰ-ϿЀ-ӿ]{3,}', p)), default='')
    t = re.sub(r'\.(html?|php|aspx?|ece|cms)$', '', best); t = re.sub(r'[-_+]+', ' ', t); t = re.sub(r'\b\d{4,}\b', ' ', t); t = re.sub(r'\s+', ' ', t).strip()
    return (t[:1].upper() + t[1:])[:110] if len(re.findall(r'[^\W\d_]{3,}', t)) >= 3 else ''

def source_of(url):
    """The site of an article, from its address; empty when the address cannot be read."""
    try: return re.sub(r'^www\.', '', urllib.parse.urlparse(url).netloc.split(':')[0])
    except Exception: return ''

def load(last):
    """The reports themselves, up to `last`. elsewhere: the article was found in GDELT's knowledge graph and under half of the places it names are in the country of the report."""
    parts = [pd.read_csv(os.path.join(REP, 'base.csv.gz'), keep_default_na=False, na_values=[''], dtype={'code': str})]
    parts += [pd.read_csv(os.path.join(REP, f), keep_default_na=False, na_values=[''], dtype={'code': str}) for f in sorted(os.listdir(REP)) if f[:8].isdigit() and int(f[:8]) > BASE_LAST_ADDED]
    R = pd.concat(parts, ignore_index=True); R = R[R.fips.isin(NAME)].copy(); R['date'] = pd.to_datetime(R.day.astype(str), format='%Y%m%d', errors='coerce'); R = R[R.date.notna() & (R.date <= last)].copy(); R['country'] = R.fips.map(NAME)
    if 'own_share' not in R: R['own_share'] = float('nan')
    R['own_share'] = pd.to_numeric(R.own_share, errors='coerce'); R['elsewhere'] = R.own_share.notna() & (R.own_share < MAJORITY); return R

def located(R, days, countries):
    """By day and country, over seven days: reports that are not 'elsewhere', and days with at least one. Empty before the places are known for the whole week."""
    L = R[~R.elsewhere].groupby(['date', 'fips']).size().unstack().reindex(index=days, columns=countries).fillna(0); l7 = L.rolling(7).sum(); d7 = (L > 0).rolling(7).sum()
    early = days < PLACES_FROM + pd.Timedelta(days=6); l7[early] = float('nan'); d7[early] = float('nan'); return l7, d7

def main(last, R=None):
    R = load(last) if R is None else R
    m = R[R.date > last - pd.Timedelta(days=28)].copy(); m['form'] = m.code.str[:3].map(FORM).fillna('Other protest')
    F = m.groupby(['country', 'form']).size().rename('reports').reset_index(); F['share'] = (100 * F.reports / F.groupby('country').reports.transform('sum')).round(1)
    T = m[m.target.isin(TARGET)].assign(form='Target: ' + m.target.map(TARGET)).groupby(['country', 'form']).size().rename('reports').reset_index(); T['share'] = (100 * T.reports / T.country.map(m.groupby('country').size())).round(1)
    m['who'] = 'Actor: ' + m.actor.fillna('').astype(str).map(ACTOR); P = m.groupby(['country', 'who']).size().rename('reports').reset_index().rename(columns={'who': 'form'}); P['share'] = (100 * P.reports / P.country.map(m.groupby('country').size())).round(1)
    pd.concat([F, T, P], ignore_index=True).sort_values(['country', 'reports'], ascending=[True, False]).to_csv(os.path.join(OUT, 'forms.csv'), index=False)
    w = R[(R.date > last - pd.Timedelta(days=7)) & R.url.fillna('').str.startswith('http')]; busy = w.groupby('country').size(); w = w[w.country.isin(busy[busy >= 5].index)]
    A = w.groupby(['country', 'url']).agg(reports=('day', 'size'), first_day=('date', 'min'), about=('own_share', 'first')).reset_index().sort_values(['country', 'reports', 'first_day'], ascending=[True, False, False])
    A['title'] = A.url.map(title_of); A['source'] = A.url.map(source_of); A['about'] = (100 * A.about).round()          # share of the places the article names that are in the country, in per cent; empty when unknown
    A['rank'] = A.groupby('country').cumcount() + 1; A = A[A['rank'] <= 8]; A['first_day'] = A.first_day.dt.strftime('%Y-%m-%d')
    A[['country', 'rank', 'title', 'source', 'url', 'reports', 'first_day', 'about']].to_csv(os.path.join(OUT, 'articles.csv'), index=False)
    return len(F), len(A), R[R.date > last - pd.Timedelta(days=7)].groupby('country').url.nunique().to_dict()
