"""
Synthetic data generator for the "FP&A Analytics in Microsoft Fabric" project.

Creates a fully fictional dataset for NitroVista Chemicals S.A., a mid-size
producer of nitrogen fertilizers and industrial chemicals:

  data/raw/erp/sales_invoices.csv        - invoice lines exported from the sales module
  data/raw/erp/gl_cost_postings.csv      - cost postings exported from a Polish ERP
                                           (semicolon separated, decimal comma, dd.mm.yyyy)
  data/raw/budget/budget_2025_2026.xlsx  - budget workbook in the typical "months as columns" layout
  data/raw/master_data/*.csv             - products, customers, cost centers, chart of accounts

Actual EUR invoices are stored in EUR only. They are converted to PLN inside Fabric
using real NBP exchange rates, so the FX variance in the report is based on real data.

All company names, customers and figures are invented. Run:  python scripts/generate_data.py
"""

from __future__ import annotations

import calendar
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SEED = 2025
rng = np.random.default_rng(SEED)
random.seed(SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

BUDGET_YEARS = [2025, 2026]
ACTUAL_START = date(2025, 1, 1)
ACTUAL_END = date(2026, 8, 31)  # last closed month
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# ---------------------------------------------------------------------------
# Master data
# ---------------------------------------------------------------------------
PRODUCTS = pd.DataFrame(
    [
        # id, name, group, production cost center, budget volume 2025 (t), domestic share,
        # budget price 2025 PLN/t, budget price 2025 EUR/t, gas MWh/t, CO2 t/t
        ("P01", "Urea 46%", "Fertilizers", "PRD-01", 180_000, 0.65, 2300, 530, 5.0, 0.7),
        ("P02", "Ammonium Nitrate 34%", "Fertilizers", "PRD-02", 240_000, 0.70, 1900, 440, 3.2, 0.5),
        ("P03", "UAN 32 Solution", "Fertilizers", "PRD-03", 150_000, 0.60, 1500, 350, 2.7, 0.4),
        ("P04", "Calcium Ammonium Nitrate 27%", "Fertilizers", "PRD-02", 120_000, 0.65, 1700, 390, 2.5, 0.4),
        ("P05", "Technical Ammonia", "Industrial Chemicals", "PRD-01", 60_000, 0.50, 2600, 600, 9.0, 1.6),
        ("P06", "AdBlue (AUS32)", "Industrial Chemicals", "PRD-03", 90_000, 0.40, 1400, 320, 1.2, 0.2),
    ],
    columns=[
        "product_id", "product_name", "product_group", "production_cost_center",
        "vol_2025", "domestic_share", "price_pln", "price_eur", "gas_mwh_t", "co2_t_t",
    ],
)

FERT_SEASON = [0.09, 0.11, 0.13, 0.11, 0.08, 0.06, 0.07, 0.07, 0.08, 0.07, 0.06, 0.07]
CHEM_SEASON = [0.085, 0.08, 0.085, 0.085, 0.085, 0.08, 0.08, 0.08, 0.085, 0.085, 0.085, 0.085]

COST_CENTERS = pd.DataFrame(
    [
        ("PRD-01", "Ammonia & Urea Unit", "Production"),
        ("PRD-02", "Nitrates Unit", "Production"),
        ("PRD-03", "Solutions & AdBlue Unit", "Production"),
        ("LOG-01", "Logistics", "Logistics"),
        ("MNT-01", "Maintenance", "Maintenance"),
        ("SAL-01", "Sales & Marketing", "Sales"),
        ("ADM-01", "Administration", "Administration"),
    ],
    columns=["cost_center", "cost_center_name", "department"],
)

ACCOUNTS = pd.DataFrame(
    [
        # account, name, pl_line, pl_line_order, cost_behavior
        ("701-01", "Revenue from sales of products", "Revenue", 1, "Revenue"),
        ("401-01", "Natural gas", "Variable costs", 2, "Variable"),
        ("401-02", "Electricity", "Variable costs", 2, "Variable"),
        ("401-03", "Other raw materials & catalysts", "Variable costs", 2, "Variable"),
        ("403-02", "CO2 emission allowances", "Variable costs", 2, "Variable"),
        ("402-01", "Transport & freight", "Variable costs", 2, "Variable"),
        ("404-01", "Salaries", "Fixed costs", 3, "Fixed"),
        ("405-01", "Social security & benefits", "Fixed costs", 3, "Fixed"),
        ("402-02", "Maintenance & repairs", "Fixed costs", 3, "Fixed"),
        ("403-01", "Taxes & fees", "Fixed costs", 3, "Fixed"),
        ("409-01", "Other operating costs", "Fixed costs", 3, "Fixed"),
        ("400-01", "Depreciation & amortization", "Depreciation", 4, "Fixed"),
    ],
    columns=["account", "account_name", "pl_line", "pl_line_order", "cost_behavior"],
)

CUSTOMERS = pd.DataFrame(
    [
        ("C001", "AgroPol Dystrybucja Sp. z o.o.", "PL", "Distributor"),
        ("C002", "Rolnik Plus S.A.", "PL", "Distributor"),
        ("C003", "Spółdzielnia Rolnicza Kujawy", "PL", "Farm cooperative"),
        ("C004", "Zielone Pola Sp. z o.o.", "PL", "Distributor"),
        ("C005", "Mazowiecka Grupa Producentów Rolnych", "PL", "Farm cooperative"),
        ("C006", "Nawozy Centrum Sp. z o.o.", "PL", "Distributor"),
        ("C007", "Podlaskie Zakłady Rolne S.A.", "PL", "Farm cooperative"),
        ("C008", "ChemTrade Polska Sp. z o.o.", "PL", "Industrial"),
        ("C009", "EkoTrans Logistyka Sp. z o.o.", "PL", "Industrial"),
        ("C010", "Wielkopolska Agro Sp. z o.o.", "PL", "Distributor"),
        ("C011", "Śląskie Hurtownie Chemiczne S.A.", "PL", "Industrial"),
        ("C012", "Lubelskie Centrum Nawozowe Sp. z o.o.", "PL", "Distributor"),
        ("C013", "Agrarhandel Nord GmbH", "DE", "Distributor"),
        ("C014", "Feldmann Düngemittel GmbH", "DE", "Distributor"),
        ("C015", "Rheinchem Industrie AG", "DE", "Industrial"),
        ("C016", "AgroMorava a.s.", "CZ", "Distributor"),
        ("C017", "Chemspol Brno s.r.o.", "CZ", "Industrial"),
        ("C018", "Coopérative Agricole du Nord", "FR", "Farm cooperative"),
        ("C019", "Engrais Atlantique SAS", "FR", "Distributor"),
        ("C020", "Delta Agri B.V.", "NL", "Distributor"),
        ("C021", "Baltic Agro UAB", "LT", "Distributor"),
        ("C022", "Danube Fertilizers Kft.", "HU", "Distributor"),
        ("C023", "Nordic Diesel Solutions AB", "SE", "Industrial"),
        ("C024", "Slovakia Agro Trade s.r.o.", "SK", "Distributor"),
    ],
    columns=["customer_id", "customer_name", "country", "segment"],
)
CUSTOMERS["market"] = np.where(CUSTOMERS["country"] == "PL", "Domestic", "Export")
CUSTOMERS["currency"] = np.where(CUSTOMERS["market"] == "Domestic", "PLN", "EUR")
# price tier: individual discount / premium vs list price
CUSTOMERS["price_tier"] = rng.uniform(-0.03, 0.02, len(CUSTOMERS)).round(4)

# which segment buys which product group
SEGMENT_PRODUCTS = {
    "Distributor": ["P01", "P02", "P03", "P04", "P06"],
    "Farm cooperative": ["P01", "P02", "P03", "P04"],
    "Industrial": ["P05", "P06", "P01"],
}

# ---------------------------------------------------------------------------
# Budget assumptions
# ---------------------------------------------------------------------------
ASSUMPTIONS = pd.DataFrame(
    [
        # year, EUR/PLN, gas PLN/MWh, electricity PLN/MWh, CO2 PLN/t
        (2025, 4.30, 190.0, 550.0, 320.0),
        (2026, 4.25, 175.0, 530.0, 330.0),
    ],
    columns=["Year", "EUR_PLN", "Gas_PLN_MWh", "Electricity_PLN_MWh", "CO2_PLN_t"],
)
ELEC_MWH_T = 0.25
OTHER_RM_PLN_T = 60.0
TRANSPORT_PLN_T = {"Domestic": 60.0, "Export": 120.0}

VOLUME_GROWTH = {2025: 1.00, 2026: 1.03}
PRICE_CHANGE = {2025: 1.00, 2026: 0.98}

# Annual fixed cost budget 2025 (PLN) by account and cost center
FIXED_2025 = {
    ("404-01", "PRD-01"): 52e6, ("404-01", "PRD-02"): 45e6, ("404-01", "PRD-03"): 30e6,
    ("404-01", "LOG-01"): 15e6, ("404-01", "MNT-01"): 32e6, ("404-01", "SAL-01"): 20e6,
    ("404-01", "ADM-01"): 28e6,
    ("402-02", "MNT-01"): 42e6, ("402-02", "PRD-01"): 15e6, ("402-02", "PRD-02"): 10e6,
    ("402-02", "PRD-03"): 6e6,
    ("400-01", "PRD-01"): 55e6, ("400-01", "PRD-02"): 32e6, ("400-01", "PRD-03"): 25e6,
    ("400-01", "LOG-01"): 8e6, ("400-01", "ADM-01"): 7e6,
    ("403-01", "ADM-01"): 12e6,
    ("409-01", "ADM-01"): 18e6, ("409-01", "SAL-01"): 10e6, ("409-01", "LOG-01"): 4e6,
}
SOCIAL_RATE = 0.205
FIXED_GROWTH_2026 = {"404-01": 1.05, "402-02": 1.00, "400-01": 1.04, "403-01": 1.03, "409-01": 1.02}
TURNAROUND_BUDGET = {(2025, 8, "MNT-01"): 18e6, (2025, 8, "PRD-01"): 7e6}  # planned ammonia turnaround


def month_iter(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def season(product_id: str, month: int) -> float:
    grp = PRODUCTS.set_index("product_id").at[product_id, "product_group"]
    return (FERT_SEASON if grp == "Fertilizers" else CHEM_SEASON)[month - 1]


# ---------------------------------------------------------------------------
# 1. Budget
# ---------------------------------------------------------------------------
def build_budget():
    vol_rows, price_rows = [], []
    for year in BUDGET_YEARS:
        for p in PRODUCTS.itertuples():
            annual = p.vol_2025 * VOLUME_GROWTH[year]
            for market, share in (("Domestic", p.domestic_share), ("Export", 1 - p.domestic_share)):
                months = [round(annual * share * season(p.product_id, m) / 100) * 100 for m in range(1, 13)]
                if year == 2025 and p.product_id in ("P01", "P05"):
                    months[7] = round(months[7] * 0.75 / 100) * 100  # planned turnaround in August
                vol_rows.append([year, p.product_id, market] + months)
                if market == "Domestic":
                    price_rows.append([year, p.product_id, market, "PLN", round(p.price_pln * PRICE_CHANGE[year], 2)])
                else:
                    price_rows.append([year, p.product_id, market, "EUR", round(p.price_eur * PRICE_CHANGE[year], 2)])
    vol = pd.DataFrame(vol_rows, columns=["Year", "Product_ID", "Market"] + MONTHS)
    price = pd.DataFrame(price_rows, columns=["Year", "Product_ID", "Market", "Currency", "Price_per_t"])

    # cost budget
    cost = {}  # (year, account, cc) -> [12]

    def add(year, acc, cc, month, amount):
        cost.setdefault((year, acc, cc), [0.0] * 12)[month - 1] += amount

    for year in BUDGET_YEARS:
        a = ASSUMPTIONS.set_index("Year").loc[year]
        for r in vol[vol["Year"] == year].itertuples(index=False):
            p = PRODUCTS.set_index("product_id").loc[r.Product_ID]
            cc = p.production_cost_center
            for mi, mname in enumerate(MONTHS, start=1):
                q = getattr(r, mname)
                add(year, "401-01", cc, mi, q * p.gas_mwh_t * a.Gas_PLN_MWh)
                add(year, "401-02", cc, mi, q * ELEC_MWH_T * a.Electricity_PLN_MWh)
                add(year, "401-03", cc, mi, q * OTHER_RM_PLN_T)
                add(year, "403-02", cc, mi, q * p.co2_t_t * a.CO2_PLN_t)
                add(year, "402-01", "LOG-01", mi, q * TRANSPORT_PLN_T[r.Market])
        for (acc, cc), annual in FIXED_2025.items():
            amt = annual * (FIXED_GROWTH_2026.get(acc, 1.0) if year == 2026 else 1.0)
            for mi in range(1, 13):
                add(year, acc, cc, mi, amt / 12)
                if acc == "404-01":
                    add(year, "405-01", cc, mi, amt / 12 * SOCIAL_RATE)
        for (y, mi, cc), amt in TURNAROUND_BUDGET.items():
            if y == year:
                add(year, "402-02", cc, mi, amt)

    cost_rows = [[y, acc, cc] + [round(v, -2) for v in vals] for (y, acc, cc), vals in sorted(cost.items())]
    cost_df = pd.DataFrame(cost_rows, columns=["Year", "Account", "Cost_Center"] + MONTHS)
    return vol, price, cost_df


# ---------------------------------------------------------------------------
# 2. Actuals - business story
# ---------------------------------------------------------------------------
def volume_factor(pid: str, y: int, m: int) -> float:
    f = 1 + rng.normal(0, 0.04)
    if (y, m) == (2025, 8) and pid in ("P01", "P05"):
        f *= 0.72  # turnaround took 10 days longer than planned
    if y == 2025 and m in (4, 5) and pid in ("P01", "P02", "P03", "P04"):
        f *= 0.93  # dry spring, weaker fertilizer demand
    if y == 2026 and m in (1, 2, 3) and pid in ("P01", "P02", "P03", "P04"):
        f *= 1.06  # strong pre-season demand
    if (y, m) == (2026, 7) and pid in ("P02", "P04"):
        f *= 0.68  # unplanned outage at the nitrates unit
    return f


def price_factor(market: str, y: int, m: int) -> float:
    f = 1 + rng.normal(0, 0.012)
    if y == 2025 and m <= 6:
        f *= 0.965  # weak market in H1 2025
    if y == 2025 and m >= 9:
        f *= 1.02
    if y == 2026 and 4 <= m <= 6 and market == "Export":
        f *= 1.06  # strong export prices in Q2 2026
    if y == 2026 and m >= 7:
        f *= 1.01
    return f


ACTUAL_GAS = {  # PLN/MWh
    (2025, 1): 205, (2025, 2): 210, (2025, 3): 198, (2025, 4): 188, (2025, 5): 182, (2025, 6): 180,
    (2025, 7): 183, (2025, 8): 186, (2025, 9): 190, (2025, 10): 195, (2025, 11): 200, (2025, 12): 204,
    (2026, 1): 238, (2026, 2): 252, (2026, 3): 221, (2026, 4): 186, (2026, 5): 178, (2026, 6): 174,
    (2026, 7): 176, (2026, 8): 179,
}
ACTUAL_CO2 = {k: v for k, v in zip(ACTUAL_GAS, [312, 318, 305, 298, 301, 309, 315, 322, 318, 325, 330, 334,
                                                 341, 346, 338, 329, 324, 327, 331, 335])}


PL_HOLIDAYS = {date(y, m, d) for y in (2025, 2026) for m, d in
               [(1, 1), (1, 6), (5, 1), (5, 3), (8, 15), (11, 1), (11, 11), (12, 24), (12, 25), (12, 26)]}
PL_HOLIDAYS |= {date(2025, 4, 21), date(2025, 6, 19), date(2026, 4, 6), date(2026, 6, 4)}  # Easter Monday, Corpus Christi


def business_days(y: int, m: int):
    last = calendar.monthrange(y, m)[1]
    days = (date(y, m, d) for d in range(1, last + 1))
    return [d for d in days if d.weekday() < 5 and d not in PL_HOLIDAYS]


def build_actuals(vol_budget: pd.DataFrame, price_budget: pd.DataFrame):
    prod = PRODUCTS.set_index("product_id")
    invoices, gl = [], []
    inv_counter = {}
    actual_qty = {}  # (y, m, pid, market) -> qty (for cost drivers)

    for y, m in month_iter(ACTUAL_START, ACTUAL_END):
        bdays = business_days(y, m)
        for pid in PRODUCTS["product_id"]:
            for market in ("Domestic", "Export"):
                bq = vol_budget.query("Year == @y and Product_ID == @pid and Market == @market")[MONTHS[m - 1]].iat[0]
                bp = price_budget.query("Year == @y and Product_ID == @pid and Market == @market")["Price_per_t"].iat[0]
                target_qty = bq * volume_factor(pid, y, m)
                list_price = bp * price_factor(market, y, m)
                seg_ok = [s for s, plist in SEGMENT_PRODUCTS.items() if pid in plist]
                custs = CUSTOMERS[(CUSTOMERS["market"] == market) & (CUSTOMERS["segment"].isin(seg_ok))]
                weights = rng.dirichlet(np.ones(len(custs)) * 2)
                done = 0.0
                for c, w in zip(custs.itertuples(), weights):
                    cust_qty = target_qty * w
                    while cust_qty > 20:
                        lot = min(cust_qty, float(rng.choice([24, 25, 50, 100, 250, 500, 800, 1200], p=[.1, .15, .1, .15, .2, .15, .1, .05])))
                        lot = round(lot, 1)
                        cust_qty -= lot
                        done += lot
                        unit_price = round(list_price * (1 + c.price_tier) * (1 + rng.normal(0, 0.008)), 2)
                        prefix = "FV" if market == "Domestic" else "FVX"
                        key = (prefix, y, m)
                        inv_counter[key] = inv_counter.get(key, 0) + 1
                        inv_no = f"{prefix}/{y}/{m:02d}/{inv_counter[key]:05d}"
                        inv_date = random.choice(bdays)
                        invoices.append([inv_no, 1, inv_date.isoformat(), "INV", c.customer_id, pid, lot,
                                         unit_price, c.currency, round(lot * unit_price, 2)])
                        # ~1% credit notes (returns / quality claims)
                        if rng.random() < 0.01:
                            key_cn = ("KOR", y, m)
                            inv_counter[key_cn] = inv_counter.get(key_cn, 0) + 1
                            cn_qty = -round(lot * rng.uniform(0.05, 0.3), 1)
                            cn_date = min(inv_date + timedelta(days=int(rng.integers(3, 12))), bdays[-1])
                            invoices.append([f"KOR/{y}/{m:02d}/{inv_counter[key_cn]:05d}", 1, cn_date.isoformat(), "CN",
                                             c.customer_id, pid, cn_qty, unit_price, c.currency,
                                             round(cn_qty * unit_price, 2)])
                            done += cn_qty
                actual_qty[(y, m, pid, market)] = done

        # ---- cost postings for the month -------------------------------------------------
        last_day = date(y, m, calendar.monthrange(y, m)[1])
        doc = [0]

        def post(acc, cc, amount, desc, n_split=1, day=None):
            parts = rng.dirichlet(np.ones(n_split) * 3) if n_split > 1 else [1.0]
            for part in parts:
                doc[0] += 1
                d = day or random.choice(bdays)
                gl.append([f"PK/{y}/{m:02d}/{doc[0]:04d}", d.strftime("%d.%m.%Y"), acc, cc,
                           round(amount * part, 2), desc])

        a = ASSUMPTIONS.set_index("Year").loc[y]
        cc_qty = {}
        for (yy, mm, pid, market), q in actual_qty.items():
            if (yy, mm) != (y, m):
                continue
            p = prod.loc[pid]
            cc_qty.setdefault(p.production_cost_center, []).append((pid, market, q))
        transport = 0.0
        for cc, items in cc_qty.items():
            gas = sum(q * prod.at[pid, "gas_mwh_t"] for pid, _, q in items) * (1 + rng.normal(0, 0.015))
            post("401-01", cc, gas * ACTUAL_GAS[(y, m)], f"Faktura - gaz ziemny {m:02d}/{y}", 3)
            elec = sum(q for _, _, q in items) * ELEC_MWH_T * a.Electricity_PLN_MWh * (1 + rng.normal(0.01, 0.03))
            post("401-02", cc, elec, f"Faktura - energia elektryczna {m:02d}/{y}", 2)
            post("401-03", cc, sum(q for _, _, q in items) * OTHER_RM_PLN_T * (1 + rng.normal(0.02, 0.05)),
                 "Zużycie surowców i katalizatorów", 4)
            co2 = sum(q * prod.at[pid, "co2_t_t"] for pid, _, q in items)
            post("403-02", cc, co2 * ACTUAL_CO2[(y, m)], "Rozliczenie uprawnień do emisji CO2", 1, last_day)
            transport += sum(q * TRANSPORT_PLN_T[mk] for _, mk, q in items)
        post("402-01", "LOG-01", transport * (1 + rng.normal(0.03, 0.03)), "Usługi transportowe", 6)

        for (acc, cc), annual in FIXED_2025.items():
            amt = annual * (FIXED_GROWTH_2026.get(acc, 1.0) if y == 2026 else 1.0) / 12
            if acc == "404-01":
                amt *= 1.0 + (0.02 if y == 2026 else 0.0) + rng.normal(0, 0.01)  # wage pressure in 2026
                if (y, m) == (2025, 12):
                    amt *= 1.35  # annual bonus accrual
                post(acc, cc, amt, f"Lista płac {m:02d}/{y}", 1, last_day)
                post("405-01", cc, amt * SOCIAL_RATE, f"Narzuty ZUS {m:02d}/{y}", 1, last_day)
            elif acc == "400-01":
                post(acc, cc, amt, f"Odpisy amortyzacyjne {m:02d}/{y}", 1, last_day)
            elif acc == "402-02":
                amt *= 1 + rng.normal(0.02, 0.12)
                if (y, m) == (2025, 8):
                    amt += {"MNT-01": 29e6, "PRD-01": 9e6}.get(cc, 0)  # extended turnaround
                if (y, m) == (2026, 7) and cc in ("MNT-01", "PRD-02"):
                    amt += 6.5e6 if cc == "MNT-01" else 2e6  # unplanned outage repair
                post(acc, cc, amt, "Usługi remontowe", 5)
            else:
                post(acc, cc, amt * (1 + rng.normal(0, 0.06)),
                     "Podatki i opłaty" if acc == "403-01" else "Pozostałe koszty operacyjne", 3)

    inv = pd.DataFrame(invoices, columns=["invoice_no", "invoice_line", "invoice_date", "doc_type", "customer_id",
                                          "product_id", "quantity_t", "unit_price", "currency", "net_amount"])
    inv = inv.sort_values(["invoice_date", "invoice_no"]).reset_index(drop=True)
    gl_df = pd.DataFrame(gl, columns=["Nr_dokumentu", "Data_ksiegowania", "Konto", "MPK", "Kwota", "Opis"])
    return inv, gl_df


def inject_quality_issues(inv: pd.DataFrame) -> pd.DataFrame:
    """Real ERP exports are never perfectly clean - add a few issues to fix in the silver layer."""
    inv = inv.copy()
    dup = inv.sample(18, random_state=SEED)  # duplicated export rows
    idx = inv.sample(25, random_state=SEED + 1).index  # sloppy customer codes
    inv.loc[idx[:12], "customer_id"] = inv.loc[idx[:12], "customer_id"].str.lower()
    inv.loc[idx[12:], "customer_id"] = inv.loc[idx[12:], "customer_id"] + " "
    inv = pd.concat([inv, dup]).sort_values(["invoice_date", "invoice_no"]).reset_index(drop=True)
    return inv


# ---------------------------------------------------------------------------
# 3. Write files
# ---------------------------------------------------------------------------
def write_budget_xlsx(vol, price, cost, path: Path):
    header_fill = PatternFill("solid", fgColor="1F4E78")
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        ASSUMPTIONS.to_excel(xw, sheet_name="Assumptions", index=False)
        vol.to_excel(xw, sheet_name="Sales_Volume", index=False)
        price.to_excel(xw, sheet_name="Sales_Price", index=False)
        cost.to_excel(xw, sheet_name="Cost_Budget", index=False)
        for ws in xw.book.worksheets:
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
            for col in range(1, ws.max_column + 1):
                ws.column_dimensions[get_column_letter(col)].width = 14
                for row in range(2, ws.max_row + 1):
                    c = ws.cell(row=row, column=col)
                    if isinstance(c.value, (int, float)) and col > 3:
                        c.number_format = "#,##0" if ws.title != "Assumptions" else "0.00"
            ws.freeze_panes = "D2" if ws.title != "Assumptions" else "B2"


def main():
    for sub in ("erp", "budget", "master_data"):
        (RAW / sub).mkdir(parents=True, exist_ok=True)

    vol, price, cost = build_budget()
    inv, gl = build_actuals(vol, price)
    inv = inject_quality_issues(inv)

    inv.to_csv(RAW / "erp" / "sales_invoices.csv", index=False, encoding="utf-8")
    gl_out = gl.copy()
    gl_out["Kwota"] = gl_out["Kwota"].map(lambda v: f"{v:.2f}".replace(".", ","))
    gl_out.to_csv(RAW / "erp" / "gl_cost_postings.csv", index=False, sep=";", encoding="utf-8")
    write_budget_xlsx(vol, price, cost, RAW / "budget" / "budget_2025_2026.xlsx")

    PRODUCTS[["product_id", "product_name", "product_group", "production_cost_center"]].assign(unit="t") \
        .to_csv(RAW / "master_data" / "products.csv", index=False)
    CUSTOMERS[["customer_id", "customer_name", "country", "market", "currency", "segment"]] \
        .to_csv(RAW / "master_data" / "customers.csv", index=False, encoding="utf-8")
    COST_CENTERS.to_csv(RAW / "master_data" / "cost_centers.csv", index=False)
    ACCOUNTS.to_csv(RAW / "master_data" / "accounts.csv", index=False)

    print(f"sales_invoices.csv   {len(inv):>6} rows")
    print(f"gl_cost_postings.csv {len(gl):>6} rows")
    print(f"budget workbook      {len(vol)} volume rows, {len(price)} price rows, {len(cost)} cost rows")


if __name__ == "__main__":
    main()
