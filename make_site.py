"""Student-protest tracker. Copies the tables of the page into docs/data/. Usage: python make_site.py"""
import os, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); DATA = os.path.join(HERE, 'docs', 'data'); os.makedirs(DATA, exist_ok=True)
TABLES = {'latest': ['country', 'country_fr', 'region', 'region_fr', 'tracked', 'reports', 'active_days', 'reports_per_week', 'data', 'share', 'usual', 'percentile', 'percentile_season', 'tier', 'signal', 'located', 'run_days', 'far_days_year', 'press', 'articles'], 'recent': ['day', 'country', 'share', 'reports'], 'monthly': ['month', 'country', 'share', 'reports'], 'world': ['day', 'world'], 'info': ['last_day', 'pulled_at', 'reports_last_7_days', 'checks', 'incomplete', 'history_from', 'far_median', 'far_days_at_least_now', 'far_episodes_at_least_now', 'freq_elevated', 'freq_high', 'freq_exceptional'], 'forms': ['country', 'form', 'reports', 'share'], 'articles': ['country', 'rank', 'title', 'source', 'url', 'reports', 'first_day', 'about']}
for t, cols in TABLES.items():
    T = pd.read_csv(os.path.join(OUT, t + '.csv'), dtype=str, keep_default_na=False)
    if t == 'latest': T = T[T.tracked == '1']
    T[cols].to_csv(os.path.join(DATA, t + '.csv'), index=False, lineterminator='\n')
open(os.path.join(HERE, 'docs', '.nojekyll'), 'w').close()
