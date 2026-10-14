"""Synthetic inputs for the 2027 sales plan (NitroVista Chemicals, fictional)."""
import pandas as pd, numpy as np
import pathlib
R = str(pathlib.Path(__file__).resolve().parents[1] / 'data' / 'raw') + '/'
OUT = R + 'plan/'
import os; os.makedirs(OUT, exist_ok=True)

s = pd.read_csv(R+'erp/sales_invoices.csv').drop_duplicates(['invoice_no','invoice_line'])
c = pd.read_csv(R+'master_data/customers.csv')
s['customer_id'] = s.customer_id.str.strip().str.upper()
s = s.merge(c[['customer_id','market']], on='customer_id')
s['d'] = pd.to_datetime(s.invoice_date); s = s[s.d.dt.year == 2025]
s['m'] = s.d.dt.month
g = s.groupby(['product_id','market','m']).agg(q=('quantity_t','sum'), v=('net_amount','sum')).reset_index()
price = g.groupby(['product_id','market']).apply(lambda x: x.v.sum()/x.q.sum(), include_groups=False).rename('p').reset_index()

FX_BASE = 4.28
months = pd.date_range('2027-01-01', '2027-12-01', freq='MS')

# ---- FX scenarios ------------------------------------------------------
fx = pd.DataFrame([(sc, m.date(), r) for sc, r in [('Base',4.28),('Strong PLN',4.15),('Weak PLN',4.45)] for m in months],
                  columns=['scenario','month_start','eur_pln'])
fx.to_csv(OUT+'fx_scenarios_2027.csv', index=False)

# ---- plan seed: 2025 volumes +3%, prices +2%, currency mix ------------
mix = {('Domestic','PLN'):0.95, ('Domestic','EUR'):0.05, ('Export','EUR'):0.85, ('Export','PLN'):0.15}
rows = []
for _, r in g.iterrows():
    base_p = price[(price.product_id==r.product_id)&(price.market==r.market)].p.iloc[0]  # in market currency
    native = 'PLN' if r.market=='Domestic' else 'EUR'
    for cur in ['PLN','EUR']:
        share = mix[(r.market,cur)]
        q = round(r.q * 1.03 * share, 0)
        p = base_p if cur == native else (base_p/FX_BASE if cur=='EUR' else base_p*FX_BASE)
        rows.append((r.product_id, r.market, cur, months[r.m-1].date(), q, round(p*1.02, 2)))
seed = pd.DataFrame(rows, columns=['product_id','market','currency','month_start','quantity_t','price_cur'])
seed.to_csv(OUT+'plan_seed_2027.csv', index=False)

# ---- production capacity: flat, ammonia plant turnaround in August ----
annual = g.groupby('product_id').q.sum()
cap = []
for pid, q in annual.items():
    for m in months:
        f = 0.35 if (pid in ('P01','P05') and m.month == 8) else 1.0
        note = 'Planned turnaround – ammonia plant' if f < 1 else ''
        cap.append((pid, m.date(), round(q*1.05/12*f, -1), note))
cap = pd.DataFrame(cap, columns=['product_id','month_start','capacity_t','note'])
cap.to_csv(OUT+'production_capacity_2027.csv', index=False)

# ---- opening stock 1 Jan 2027 + warehouse limit -----------------------
avg = annual/12
OPEN = {'P01':1.45,'P02':2.0,'P03':1.6,'P04':1.7,'P05':0.9,'P06':0.6}
op = pd.DataFrame({'product_id': avg.index,
                   'opening_stock_t': [round(v*OPEN[pid], -1) for pid, v in avg.items()],
                   'max_storage_t': [round(v*(3.0 if pid<'P05' else 1.5), -1) for pid, v in avg.items()]})
op.to_csv(OUT+'opening_stock_2027.csv', index=False)

# ---- feasibility check: closing stock with production = capacity -------
sq = seed.groupby(['product_id','month_start']).quantity_t.sum().unstack()
cp = cap.pivot(index='product_id', columns='month_start', values='capacity_t')
stock = op.set_index('product_id').opening_stock_t.copy()
res = {}
for m in sq.columns:
    stock = stock + cp[m] - sq[m]; res[m] = stock.round(0)
print(pd.DataFrame(res).T.to_string())
print(op)
