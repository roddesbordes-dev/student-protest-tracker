"""Student-protest tracker. Copies the tables of the page into docs/data/. Usage: python make_site.py"""
import os, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); DATA = os.path.join(HERE, 'docs', 'data'); os.makedirs(DATA, exist_ok=True)
for t in ('latest', 'recent', 'monthly', 'world', 'info', 'forms', 'articles'):
    T = pd.read_csv(os.path.join(OUT, t + '.csv'), dtype=str, keep_default_na=False)
    if t == 'latest':
        T = T[T.tracked == '1']; tracked = set(T.country)
        for c in ('located', 'run_days', 'far_days_year'): T[c] = T[c].str.replace(r'\.0$', '', regex=True)
    if t in ('forms', 'articles'): T = T[T.country.isin(tracked)]
    T.to_csv(os.path.join(DATA, t + '.csv'), index=False, lineterminator='\n')
open(os.path.join(HERE, 'docs', '.nojekyll'), 'w').close()
