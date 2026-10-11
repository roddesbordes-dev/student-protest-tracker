"""Student-protest tracker. Copies the tables of the page into docs/data/. Usage: python make_site.py"""
import os, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); DATA = os.path.join(HERE, 'docs', 'data'); os.makedirs(DATA, exist_ok=True)
DROP = {'latest': ['days_high', 'peak', 'peak_day'], 'info': ['far_now', 'far_share_days_at_least_now', 'backtest_days']}
for t in ('latest', 'recent', 'monthly', 'world', 'info', 'forms', 'articles'):
    T = pd.read_csv(os.path.join(OUT, t + '.csv'), dtype=str, keep_default_na=False)
    T.drop(columns=DROP.get(t, [])).to_csv(os.path.join(DATA, t + '.csv'), index=False, lineterminator='\n')
open(os.path.join(HERE, 'docs', '.nojekyll'), 'w').close()
