# Semantic model – `sm_fpa` (Direct Lake)

## Tables

| Table | Type | Grain |
|---|---|---|
| `fact_pnl` | Fact | month × scenario (Actual/Budget) × account × cost center (× product × market for revenue) |
| `fact_sales` | Fact | invoice line |
| `fact_revenue_bridge` | Fact | month × product × market (closed months) |
| `dim_date` | Dimension (mark as date table) | day |
| `dim_account`, `dim_cost_center`, `dim_product`, `dim_customer`, `dim_market` | Dimensions | |
| `dim_bridge_step` | Helper (no relationships) | 4 rows for the waterfall |

## Relationships (all many-to-one, single direction)

| From (many) | To (one) |
|---|---|
| `fact_pnl[month_start]` | `dim_date[date]` |
| `fact_pnl[account]` | `dim_account[account]` |
| `fact_pnl[cost_center]` | `dim_cost_center[cost_center]` |
| `fact_pnl[product_id]` | `dim_product[product_id]` |
| `fact_pnl[market]` | `dim_market[market]` |
| `fact_sales[invoice_date]` | `dim_date[date]` |
| `fact_sales[customer_id]` | `dim_customer[customer_id]` |
| `fact_sales[product_id]` | `dim_product[product_id]` |
| `fact_sales[market]` | `dim_market[market]` |
| `fact_revenue_bridge[month_start]` | `dim_date[date]` |
| `fact_revenue_bridge[product_id]` | `dim_product[product_id]` |
| `fact_revenue_bridge[market]` | `dim_market[market]` |

## Model settings

* Mark `dim_date` as date table (`date` column).
* Sort by column: `dim_date[month_name]` → `month_no`, `dim_account[pl_line]` → `pl_line_order`, `dim_bridge_step[step]` → `step_order`.
* Hide all key columns on fact tables and the raw `amount_pln` column – users should only see measures.
* Format measures as `#,0` (PLN) or `#,0.0,,` for millions; percentages as `0.0%`.
* Put measures in display folders: *P&L*, *KPI*, *Sales*, *Bridge*.

## Measures (DAX)

Add the measures to the `fact_pnl` table (and organise them in display folders):

```dax
-- ===== P&L (folder: P&L) =====
Actual =
CALCULATE ( SUM ( fact_pnl[amount_pln] ), fact_pnl[scenario] = "Actual" )

Budget =
CALCULATE ( SUM ( fact_pnl[amount_pln] ), fact_pnl[scenario] = "Budget" )

-- budget only for months that already have actuals – fair comparison during the year
Budget (closed months) =
CALCULATE ( [Budget], dim_date[is_closed_month] = TRUE () )

Variance =
[Actual] - [Budget (closed months)]

-- costs are negative, so dividing by ABS keeps "positive = favourable" for every line
Variance % =
DIVIDE ( [Variance], ABS ( [Budget (closed months)] ) )

Actual YTD =
TOTALYTD ( [Actual], dim_date[date] )

Budget YTD =
TOTALYTD ( [Budget (closed months)], dim_date[date] )

Variance YTD =
[Actual YTD] - [Budget YTD]

Actual PY =
CALCULATE ( [Actual], SAMEPERIODLASTYEAR ( dim_date[date] ) )

-- ===== KPI (folder: KPI) =====
Revenue =
CALCULATE ( [Actual], dim_account[pl_line] = "Revenue" )

Revenue Budget =
CALCULATE ( [Budget (closed months)], dim_account[pl_line] = "Revenue" )

Contribution Margin =
CALCULATE ( [Actual], dim_account[pl_line] IN { "Revenue", "Variable costs" } )

Contribution Margin Budget =
CALCULATE ( [Budget (closed months)], dim_account[pl_line] IN { "Revenue", "Variable costs" } )

Contribution Margin % =
DIVIDE ( [Contribution Margin], [Revenue] )

EBITDA =
CALCULATE ( [Actual], dim_account[pl_line] <> "Depreciation" )

EBITDA Budget =
CALCULATE ( [Budget (closed months)], dim_account[pl_line] <> "Depreciation" )

EBITDA vs Budget =
[EBITDA] - [EBITDA Budget]

EBITDA % =
DIVIDE ( [EBITDA], [Revenue] )

EBIT =
[Actual]

-- colour for conditional formatting of variance columns
Variance Color =
IF ( [Variance] >= 0, "#1B7F3B", "#C62828" )

-- ===== Sales (folder: Sales) =====
Sold Volume (t) =
SUM ( fact_sales[quantity_t] )

Sales PLN =
SUM ( fact_sales[net_amount_pln] )

Avg Price PLN/t =
DIVIDE ( [Sales PLN], [Sold Volume (t)] )

Export Share % =
DIVIDE ( CALCULATE ( [Sales PLN], dim_market[market] = "Export" ), [Sales PLN] )

-- ===== Bridge (folder: Bridge) =====
Volume Effect =
SUM ( fact_revenue_bridge[volume_effect_pln] )

Price Effect =
SUM ( fact_revenue_bridge[price_effect_pln] )

FX Effect =
SUM ( fact_revenue_bridge[fx_effect_pln] )

-- used in the waterfall chart with dim_bridge_step[step] on the Category axis;
-- the chart's automatic "Total" bar equals Actual revenue
Bridge Value =
SWITCH (
    SELECTEDVALUE ( dim_bridge_step[step] ),
    "Budget", SUM ( fact_revenue_bridge[budget_revenue_pln] ),
    "Volume", [Volume Effect],
    "Price", [Price Effect],
    "FX", [FX Effect]
)
-- dynamic Y-axis start for the waterfall (so the effects are visible)
Bridge Axis Min =
0.97 * MIN ( SUM ( fact_revenue_bridge[budget_revenue_pln] ), SUM ( fact_revenue_bridge[actual_revenue_pln] ) )

-- dynamic chart title, e.g. "Revenue 2025: -65.9 mln vs budget"
Bridge Title =
VAR _var = DIVIDE ( [Volume Effect] + [Price Effect] + [FX Effect], 1000000 )
RETURN
    "Revenue " & SELECTEDVALUE ( dim_date[year] ) & ": "
        & FORMAT ( _var, "+#,0.0;-#,0.0" ) & " mln vs budget"
```

## Report pages

1. **Executive summary** – KPI cards (Revenue, EBITDA, EBITDA %, EBITDA vs Budget), P&L matrix Actual vs Budget with drill-down to accounts and conditional formatting (*Variance Color*), monthly EBITDA vs budget, key takeaways, year slicer.
2. **Revenue bridge** – waterfall (`dim_bridge_step[step]` + *Bridge Value*, dynamic title and axis), effects by product (table), effects by month (stacked columns).

Ideas for further pages: cost analysis by cost center, sales detail by customer and country.
