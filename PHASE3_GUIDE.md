# Phase 3 Implementation Guide
## Application Layer and Cloud Deployment

This guide walks you through every file you need to create and every step
you need to follow to complete Phase 3 from scratch.

---

## Overview of What You Are Building

A **Streamlit dashboard** that:
- Connects live to your **Neon PostgreSQL** database
- Shows **6 interactive charts** (revenue trend, order status, category, state, sellers, payments)
- Has **3 sidebar filters** (date range, customer state, product category)
- Is deployed publicly on **Render**

---

## Step 1 — Install Dependencies

Add these two lines to the bottom of your `requirements.txt`:

```
streamlit==1.45.1
plotly==5.24.1
```

Then in your terminal (with venv active):

```bash
pip install streamlit plotly
```

---

## Step 2 — Create the `app/` folder

In your project root, create a new folder called `app/`.

```
E-Commerce-Order-Analytics-Platform/
└── app/
    ├── db.py
    ├── queries.py
    └── app.py
```

---

## Step 3 — Create `app/db.py`

This file handles the database connection with SQLAlchemy connection pooling.

```python
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

_engine = None


def get_engine():
    """Return a singleton SQLAlchemy engine with connection pooling."""
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable is not set.")
        _engine = create_engine(
            url,
            pool_size=2,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return _engine
```

**Key points for the prof:**
- Uses `os.getenv("DATABASE_URL")` — no hardcoded credentials
- `pool_size=2`, `pool_pre_ping=True`, `pool_recycle=300` — proper connection pooling for Neon

---

## Step 4 — Create `app/queries.py`

This file contains all SQL queries as builder functions. They use a
`filtered_orders` CTE so all three filters (date, state, category) are
applied consistently across every chart.

```python
"""
SQL query builders for the Streamlit dashboard.

All queries use a filtered_orders CTE as the entry point so that date,
state, and category filters are applied consistently and payment values
are never double-counted across queries.

Note on SQL injection: filter values (states, categories) are loaded
directly from the database and presented as multiselect options, so they
are never free-form user input.
"""


def _filtered_orders_cte(start, end, states, categories):
    state_join = (
        "JOIN customers c ON o.customer_id = c.customer_id"
        if states else ""
    )
    cat_joins = (
        "JOIN order_items oi ON o.order_id = oi.order_id\n"
        "        JOIN products pr ON oi.product_id = pr.product_id"
        if categories else ""
    )

    conditions = [
        f"o.order_purchase_timestamp BETWEEN '{start}' AND '{end}'"
    ]
    if states:
        s = "', '".join(states)
        conditions.append(f"c.customer_state IN ('{s}')")
    if categories:
        c = "', '".join(categories)
        conditions.append(f"pr.product_category_name IN ('{c}')")

    where = "\n          AND ".join(conditions)

    return f"""
    WITH filtered_orders AS (
        SELECT DISTINCT
            o.order_id,
            o.customer_id,
            o.order_status,
            o.order_purchase_timestamp
        FROM orders o
        {state_join}
        {cat_joins}
        WHERE {where}
    )"""


def kpis_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte},
    order_totals AS (
        SELECT order_id, SUM(payment_value) AS order_total
        FROM payments
        GROUP BY order_id
    )
    SELECT
        SUM(ot.order_total)                      AS total_revenue,
        COUNT(DISTINCT fo.order_id)              AS total_orders,
        AVG(ot.order_total)                      AS avg_order_value,
        ROUND(AVG(r.review_score)::numeric, 2)   AS avg_review_score
    FROM filtered_orders fo
    JOIN order_totals ot ON fo.order_id = ot.order_id
    LEFT JOIN reviews r  ON fo.order_id = r.order_id
    """


def monthly_revenue_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte},
    monthly AS (
        SELECT
            date_trunc('month', fo.order_purchase_timestamp)::date AS month,
            SUM(p.payment_value)               AS total_revenue,
            COUNT(DISTINCT fo.order_id)        AS total_orders
        FROM filtered_orders fo
        JOIN payments p ON fo.order_id = p.order_id
        WHERE fo.order_status != 'canceled'
        GROUP BY 1
    )
    SELECT
        month,
        total_revenue,
        total_orders,
        ROUND(
            (total_revenue - LAG(total_revenue) OVER (ORDER BY month))
            / NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0) * 100,
            2
        ) AS mom_growth_pct
    FROM monthly
    ORDER BY month
    """


def order_status_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte}
    SELECT
        fo.order_status,
        COUNT(*) AS order_count
    FROM filtered_orders fo
    GROUP BY 1
    ORDER BY 2 DESC
    """


def revenue_by_category_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte}
    SELECT
        COALESCE(pr.product_category_name, 'Unknown') AS category,
        SUM(oi.price)                                  AS total_revenue,
        COUNT(DISTINCT fo.order_id)                    AS total_orders
    FROM filtered_orders fo
    JOIN order_items oi ON fo.order_id   = oi.order_id
    JOIN products pr    ON oi.product_id = pr.product_id
    GROUP BY 1
    ORDER BY total_revenue DESC
    LIMIT 15
    """


def revenue_by_state_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte},
    order_totals AS (
        SELECT order_id, SUM(payment_value) AS order_total
        FROM payments
        GROUP BY order_id
    )
    SELECT
        c.customer_state            AS state,
        SUM(ot.order_total)         AS total_revenue,
        COUNT(DISTINCT fo.order_id) AS total_orders
    FROM filtered_orders fo
    JOIN customers c     ON fo.customer_id = c.customer_id
    JOIN order_totals ot ON fo.order_id    = ot.order_id
    GROUP BY 1
    ORDER BY total_revenue DESC
    LIMIT 20
    """


def top_sellers_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte}
    SELECT
        s.seller_id,
        s.seller_city,
        s.seller_state,
        SUM(oi.price + oi.shipping_charges)    AS total_revenue,
        COUNT(DISTINCT fo.order_id)             AS orders_fulfilled,
        ROUND(AVG(r.review_score)::numeric, 2) AS avg_review_score
    FROM filtered_orders fo
    JOIN order_items oi ON fo.order_id  = oi.order_id
    JOIN sellers s      ON oi.seller_id = s.seller_id
    LEFT JOIN reviews r ON fo.order_id  = r.order_id
    GROUP BY 1, 2, 3
    ORDER BY total_revenue DESC
    LIMIT 10
    """


def payment_type_query(start, end, states, categories):
    cte = _filtered_orders_cte(start, end, states, categories)
    return f"""
    {cte}
    SELECT
        p.payment_type,
        COUNT(DISTINCT fo.order_id) AS total_orders,
        SUM(p.payment_value)        AS total_revenue
    FROM filtered_orders fo
    JOIN payments p ON fo.order_id = p.order_id
    GROUP BY 1
    ORDER BY total_revenue DESC
    """
```

---

## Step 5 — Create `app/app.py`

This is the main Streamlit dashboard file.

```python
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from db import get_engine
from queries import (
    kpis_query,
    monthly_revenue_query,
    order_status_query,
    revenue_by_category_query,
    revenue_by_state_query,
    top_sellers_query,
    payment_type_query,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="E-Commerce Order Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for KPI cards ──────────────────────────────────────────────────

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; color: #666; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Filter options (cached — loaded once) ────────────────────────────────────


@st.cache_data(ttl=3600)
def load_filter_options():
    engine = get_engine()
    with engine.connect() as conn:
        states = pd.read_sql(
            "SELECT DISTINCT customer_state FROM customers ORDER BY 1", conn
        )["customer_state"].tolist()

        categories = pd.read_sql(
            "SELECT DISTINCT product_category_name FROM products "
            "WHERE product_category_name IS NOT NULL ORDER BY 1",
            conn,
        )["product_category_name"].tolist()

        dr = pd.read_sql(
            "SELECT MIN(order_purchase_timestamp)::date AS min_date,"
            "       MAX(order_purchase_timestamp)::date AS max_date"
            " FROM orders",
            conn,
        )
    return (
        states,
        categories,
        dr["min_date"].iloc[0],
        dr["max_date"].iloc[0],
    )


# ── Cached data loaders ───────────────────────────────────────────────────────


@st.cache_data(ttl=3600)
def fetch_kpis(start, end, states, categories):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(kpis_query(start, end, states, categories), conn)


@st.cache_data(ttl=3600)
def fetch_monthly_revenue(start, end, states, categories):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(
            monthly_revenue_query(start, end, states, categories), conn
        )


@st.cache_data(ttl=3600)
def fetch_order_status(start, end, states, categories):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(
            order_status_query(start, end, states, categories), conn
        )


@st.cache_data(ttl=3600)
def fetch_revenue_by_category(start, end, states, categories):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(
            revenue_by_category_query(start, end, states, categories), conn
        )


@st.cache_data(ttl=3600)
def fetch_revenue_by_state(start, end, states, categories):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(
            revenue_by_state_query(start, end, states, categories), conn
        )


@st.cache_data(ttl=3600)
def fetch_top_sellers(start, end, states, categories):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(
            top_sellers_query(start, end, states, categories), conn
        )


@st.cache_data(ttl=3600)
def fetch_payment_types(start, end, states, categories):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(
            payment_type_query(start, end, states, categories), conn
        )


# ── Sidebar — interactive filters ────────────────────────────────────────────

all_states, all_categories, min_date, max_date = load_filter_options()

with st.sidebar:
    st.markdown("### 🛒 E-Commerce Analytics")
    st.markdown("---")

    # Interactive widget 1: Date range (two separate pickers)
    st.markdown("📅 **Date Range**")
    start_date = st.date_input(
        "From",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
    )
    end_date = st.date_input(
        "To",
        value=max_date,
        min_value=start_date,
        max_value=max_date,
    )

    # Interactive widget 2: State multiselect
    selected_states = st.multiselect(
        "🗺️ Customer State",
        options=all_states,
        default=[],
        placeholder="All states",
        help="Filter by customer state",
    )

    # Interactive widget 3: Category multiselect
    selected_categories = st.multiselect(
        "📦 Product Category",
        options=all_categories,
        default=[],
        placeholder="All categories",
        help="Filter by product category",
    )

    st.markdown("---")
    st.caption("Data: Olist Brazilian E-Commerce (2016–2018)")
    st.caption("Course: EAS 550 — Phase 3")

# Guard: show warning if user picks end before start
if end_date < start_date:
    st.warning("⚠️ End date must be after start date. Please adjust the date range.")
    st.stop()

states_tuple = tuple(selected_states)
categories_tuple = tuple(selected_categories)

# ── Page header ───────────────────────────────────────────────────────────────

st.title("🛒 E-Commerce Order Analytics")
st.markdown(
    f"Showing data from **{start_date}** to **{end_date}**"
    + (f" · States: **{', '.join(selected_states)}**" if selected_states else "")
    + (
        f" · Categories: **{len(selected_categories)} selected**"
        if selected_categories
        else ""
    )
)
st.markdown("---")

# ── Load all data ─────────────────────────────────────────────────────────────

with st.spinner("Loading data..."):
    kpis_df = fetch_kpis(start_date, end_date, states_tuple, categories_tuple)
    monthly_df = fetch_monthly_revenue(
        start_date, end_date, states_tuple, categories_tuple
    )
    status_df = fetch_order_status(
        start_date, end_date, states_tuple, categories_tuple
    )
    category_df = fetch_revenue_by_category(
        start_date, end_date, states_tuple, categories_tuple
    )
    state_df = fetch_revenue_by_state(
        start_date, end_date, states_tuple, categories_tuple
    )
    sellers_df = fetch_top_sellers(
        start_date, end_date, states_tuple, categories_tuple
    )
    payment_df = fetch_payment_types(
        start_date, end_date, states_tuple, categories_tuple
    )

# ── Section 1: KPI Cards ─────────────────────────────────────────────────────

st.subheader("Key Metrics")

total_rev = float(kpis_df["total_revenue"].iloc[0] or 0)
total_orders = int(kpis_df["total_orders"].iloc[0] or 0)
avg_order = float(kpis_df["avg_order_value"].iloc[0] or 0)
avg_review = float(kpis_df["avg_review_score"].iloc[0] or 0)

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total Revenue", f"R$ {total_rev:,.0f}")
k2.metric("🧾 Total Orders", f"{total_orders:,}")
k3.metric("🛍️ Avg Order Value", f"R$ {avg_order:,.2f}")
k4.metric("⭐ Avg Review Score", f"{avg_review:.2f} / 5")

st.markdown("---")

# ── Section 2: Monthly Revenue Trend + Order Status ──────────────────────────

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 Monthly Revenue Trend")

    if monthly_df.empty:
        st.info("No data available for the selected filters.")
    else:
        monthly_df["month"] = pd.to_datetime(monthly_df["month"])

        fig_revenue = go.Figure()

        fig_revenue.add_trace(
            go.Scatter(
                x=monthly_df["month"],
                y=monthly_df["total_revenue"],
                mode="lines+markers",
                name="Revenue",
                line=dict(color="#1f77b4", width=2.5),
                marker=dict(size=6),
                hovertemplate="<b>%{x|%b %Y}</b><br>Revenue: R$ %{y:,.0f}<extra></extra>",
            )
        )

        mom = monthly_df.dropna(subset=["mom_growth_pct"])
        fig_revenue.add_trace(
            go.Bar(
                x=mom["month"],
                y=mom["mom_growth_pct"],
                name="MoM Growth %",
                yaxis="y2",
                marker_color=[
                    "#2ca02c" if v >= 0 else "#d62728"
                    for v in mom["mom_growth_pct"]
                ],
                opacity=0.4,
                hovertemplate="<b>%{x|%b %Y}</b><br>MoM Growth: %{y:.1f}%<extra></extra>",
            )
        )

        fig_revenue.update_layout(
            xaxis=dict(title="Month"),
            yaxis=dict(title="Revenue (R$)", tickformat=",.0f"),
            yaxis2=dict(
                title="MoM Growth %",
                overlaying="y",
                side="right",
                showgrid=False,
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            hovermode="x unified",
            height=380,
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig_revenue, use_container_width=True)

with col2:
    st.subheader("🔄 Order Status")

    if status_df.empty:
        st.info("No data.")
    else:
        fig_status = px.pie(
            status_df,
            names="order_status",
            values="order_count",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_status.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Orders: %{value:,}<br>Share: %{percent}<extra></extra>",
        )
        fig_status.update_layout(
            showlegend=False,
            height=380,
            margin=dict(t=20, b=20, l=0, r=0),
        )
        st.plotly_chart(fig_status, use_container_width=True)

st.markdown("---")

# ── Section 3: Revenue by Product Category ───────────────────────────────────

st.subheader("📦 Revenue by Product Category (Top 15)")

if category_df.empty:
    st.info("No data available for the selected filters.")
else:
    fig_cat = px.bar(
        category_df,
        x="total_revenue",
        y="category",
        orientation="h",
        color="total_revenue",
        color_continuous_scale="Blues",
        text=category_df["total_revenue"].apply(lambda v: f"R$ {v:,.0f}"),
        hover_data={"total_orders": True, "total_revenue": ":.0f"},
        labels={"total_revenue": "Revenue (R$)", "category": ""},
    )
    fig_cat.update_traces(textposition="outside")
    fig_cat.update_layout(
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        height=520,
        margin=dict(t=10, b=40, l=10, r=120),
    )
    st.plotly_chart(fig_cat, use_container_width=True)

st.markdown("---")

# ── Section 4: Revenue by State + Top Sellers ─────────────────────────────────

col3, col4 = st.columns(2)

with col3:
    st.subheader("🗺️ Revenue by Customer State")

    if state_df.empty:
        st.info("No data available for the selected filters.")
    else:
        fig_state = px.bar(
            state_df,
            x="state",
            y="total_revenue",
            color="total_revenue",
            color_continuous_scale="Teal",
            text=state_df["total_revenue"].apply(lambda v: f"R$ {v/1000:.0f}K"),
            hover_data={"total_orders": True, "total_revenue": ":.0f"},
            labels={"state": "State", "total_revenue": "Revenue (R$)"},
        )
        fig_state.update_traces(textposition="outside")
        fig_state.update_layout(
            coloraxis_showscale=False,
            height=420,
            margin=dict(t=10, b=40),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_state, use_container_width=True)

with col4:
    st.subheader("🏆 Top 10 Sellers by Revenue")

    if sellers_df.empty:
        st.info("No data available for the selected filters.")
    else:
        sellers_df["seller_label"] = (
            sellers_df["seller_id"].str[:8]
            + "… ("
            + sellers_df["seller_city"].str.title()
            + ")"
        )
        fig_sellers = px.bar(
            sellers_df,
            x="total_revenue",
            y="seller_label",
            orientation="h",
            color="avg_review_score",
            color_continuous_scale="RdYlGn",
            range_color=[1, 5],
            text=sellers_df["total_revenue"].apply(lambda v: f"R$ {v:,.0f}"),
            hover_data={
                "orders_fulfilled": True,
                "avg_review_score": True,
                "seller_state": True,
            },
            labels={
                "total_revenue": "Revenue (R$)",
                "seller_label": "",
                "avg_review_score": "Avg Rating",
            },
        )
        fig_sellers.update_traces(textposition="outside")
        fig_sellers.update_layout(
            yaxis=dict(autorange="reversed"),
            coloraxis_colorbar=dict(title="Rating"),
            height=420,
            margin=dict(t=10, b=40, r=120),
        )
        st.plotly_chart(fig_sellers, use_container_width=True)

st.markdown("---")

# ── Section 5: Payment Methods ────────────────────────────────────────────────

st.subheader("💳 Revenue by Payment Method")

if payment_df.empty:
    st.info("No data available for the selected filters.")
else:
    fig_pay = px.bar(
        payment_df,
        x="payment_type",
        y="total_revenue",
        color="payment_type",
        text=payment_df["total_revenue"].apply(lambda v: f"R$ {v/1_000_000:.2f}M"),
        hover_data={"total_orders": True},
        labels={
            "payment_type": "Payment Method",
            "total_revenue": "Revenue (R$)",
        },
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig_pay.update_traces(textposition="outside")
    fig_pay.update_layout(
        showlegend=False,
        height=360,
        margin=dict(t=10, b=40),
    )
    st.plotly_chart(fig_pay, use_container_width=True)

st.markdown("---")
st.caption(
    "Built with Streamlit · Data: Olist Brazilian E-Commerce Dataset · EAS 550 Phase 3"
)
```

---

## Step 6 — Create `render.yaml`

In the **project root** (not inside `app/`), create `render.yaml`:

```yaml
services:
  - type: web
    name: ecommerce-order-analytics
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app/app.py --server.port $PORT --server.address 0.0.0.0
    plan: free
    envVars:
      - key: DATABASE_URL
        sync: false
```

---

## Step 7 — Create `.env` for local testing

In the **project root**, create a `.env` file (this is already in `.gitignore`
so it won't be pushed to GitHub):

```
DATABASE_URL=your_neon_connection_string_here
```

Replace `your_neon_connection_string_here` with your actual Neon DB URL.
It looks like: `postgresql://user:password@host/dbname?sslmode=require`

---

## Step 8 — Test locally

```bash
# from project root with venv active
streamlit run app/app.py
```

Open http://localhost:8501 in your browser. You should see the full dashboard.

---

## Step 9 — Commit and push to GitHub

```bash
git add app/app.py app/db.py app/queries.py render.yaml requirements.txt
git commit -m "Add Phase 3: Streamlit dashboard and Render deployment"
git push origin main
```

---

## Step 10 — Deploy to Render

1. Go to [render.com](https://render.com) → sign up / log in with GitHub
2. Click **New +** → **Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` and fills in build + start commands
5. Scroll down to **Environment Variables** → Add:
   - Key: `DATABASE_URL`
   - Value: your Neon connection string
6. Select **Free** plan
7. Click **Deploy Web Service**
8. Wait ~3-5 minutes → your live URL will be shown at the top

---

## Final Checklist

- [ ] `app/db.py` created
- [ ] `app/queries.py` created
- [ ] `app/app.py` created
- [ ] `render.yaml` created in project root
- [ ] `requirements.txt` updated with streamlit and plotly
- [ ] `.env` created locally (not committed)
- [ ] App runs locally on http://localhost:8501
- [ ] Code committed and pushed to GitHub
- [ ] Deployed on Render — live URL working
- [ ] README updated with live URL
- [ ] Demo video recorded

---

## Requirements Checklist (vs Professor's rubric)

| Requirement | Where it is |
|---|---|
| 2+ distinct dynamic visualizations | `app/app.py` — 6 charts total |
| 1+ interactive widget | `app/app.py` sidebar — date range, state, category |
| `@st.cache_data` for performance | Every `fetch_*` function in `app/app.py` |
| Neon connection via connection pooling | `app/db.py` — `pool_size`, `pool_pre_ping`, `pool_recycle` |
| No `pd.read_csv` | All data from `pd.read_sql()` against live DB |
| No hardcoded credentials | `DATABASE_URL` from env var only |
| Continuous deploy from GitHub to Render | `render.yaml` + Render connected to GitHub |
| README with setup + live URL | `README.md` |
