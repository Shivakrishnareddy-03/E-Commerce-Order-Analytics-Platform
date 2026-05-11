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

    # Interactive widget 1: Date range (two separate pickers — more reliable)
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
        min_value=start_date,   # can't pick end before start
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

        # Revenue line
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

        # MoM growth bar (secondary y-axis)
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
