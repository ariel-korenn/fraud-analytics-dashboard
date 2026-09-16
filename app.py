import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="לוח בקרה - זיהוי הונאות",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Palette ("control room" dark theme)
# ---------------------------------------------------------------------------
BG = "#0a0e14"
PANEL = "#0f1420"
CARD = "#131822"
BORDER = "#232a38"
TEXT = "#e6e8eb"
MUTED = "#8a94a6"
AMBER = "#ffb020"
CYAN = "#00d9ff"
RED = "#ff3b3b"

FRAUD_LABEL, LEGIT_LABEL = "הונאה", "תקין"
COLOR_MAP = {FRAUD_LABEL: RED, LEGIT_LABEL: CYAN}

NUM_FEATURES = [
    "amount",
    "transaction_hour",
    "foreign_transaction",
    "location_mismatch",
    "device_trust_score",
    "velocity_last_24h",
    "cardholder_age",
]
FEATURE_LABELS = {
    "amount": "סכום עסקה ($)",
    "transaction_hour": "שעת עסקה",
    "foreign_transaction": "עסקה בחו\"ל",
    "location_mismatch": "אי-התאמת מיקום",
    "device_trust_score": "ציון אמון מכשיר",
    "velocity_last_24h": "קצב עסקאות (24 ש')",
    "cardholder_age": "גיל בעל הכרטיס",
}

# ---------------------------------------------------------------------------
# CSS: RTL layout + control-room styling
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'JetBrains Mono', 'Consolas', monospace !important;
}}

.stApp {{
    background-color: {BG};
}}

[data-testid="stAppViewContainer"] {{
    direction: rtl;
}}
[data-testid="stSidebar"] {{
    direction: rtl;
    background-color: {PANEL};
    border-left: 1px solid {BORDER};
}}
[data-testid="stMain"] {{
    direction: rtl;
}}
h1, h2, h3, h4, h5, p, label, span, div {{
    text-align: right;
}}

/* section title */
.section-title {{
    color: {AMBER};
    font-size: 0.8rem;
    letter-spacing: 0.15em;
    font-weight: 600;
    text-transform: uppercase;
    border-right: 3px solid {AMBER};
    padding-right: 10px;
    margin: 1.6rem 0 0.8rem 0;
}}

/* top status bar */
.ops-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid {BORDER};
    background: linear-gradient(180deg, {CARD} 0%, {PANEL} 100%);
    border-radius: 6px;
    padding: 14px 22px;
    margin-bottom: 1.2rem;
}}
.ops-title {{
    font-size: 1.4rem;
    font-weight: 700;
    color: {TEXT};
    letter-spacing: 0.03em;
}}
.ops-subtitle {{
    color: {MUTED};
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    margin-top: 2px;
}}
.ops-badge {{
    color: {CYAN};
    border: 1px solid {CYAN};
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 0.75rem;
    letter-spacing: 0.1em;
}}

/* KPI metrics as cards */
[data-testid="stMetric"] {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 14px 16px;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED} !important;
}}
[data-testid="stMetricValue"] {{
    color: {AMBER} !important;
}}

/* chart container cards */
.chart-card {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 10px 14px 2px 14px;
    margin-bottom: 0.6rem;
}}

hr {{
    border-color: {BORDER};
}}

[data-testid="stSidebar"] .stButton button {{
    width: 100%;
    border: 1px solid {AMBER};
    color: {AMBER};
    background: transparent;
}}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv("credit_card_fraud_10k.csv")
    df["status_label"] = df["is_fraud"].map({1: FRAUD_LABEL, 0: LEGIT_LABEL})
    return df


df = load_data()


def style_fig(fig, height=340):
    fig.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(color=TEXT, family="JetBrains Mono, monospace", size=12),
        margin=dict(l=10, r=10, t=30, b=10),
        height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="section-title">🎛️ פילטרים</div>', unsafe_allow_html=True)

    if st.button("↺ איפוס פילטרים"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    amt_min, amt_max = float(df.amount.min()), float(df.amount.max())
    amount_range = st.slider(
        "טווח סכום עסקה ($)", amt_min, amt_max, (amt_min, amt_max), key="amount_range"
    )

    hour_range = st.slider("טווח שעת עסקה", 0, 23, (0, 23), key="hour_range")

    categories = st.multiselect(
        "קטגוריית עסק",
        sorted(df.merchant_category.unique()),
        default=sorted(df.merchant_category.unique()),
        key="categories",
    )

    foreign_filter = st.radio('עסקה בחו"ל', ["הכל", "כן", "לא"], horizontal=True, key="foreign_filter")
    mismatch_filter = st.radio("אי-התאמת מיקום", ["הכל", "כן", "לא"], horizontal=True, key="mismatch_filter")

    trust_min, trust_max = int(df.device_trust_score.min()), int(df.device_trust_score.max())
    trust_range = st.slider("ציון אמון מכשיר", trust_min, trust_max, (trust_min, trust_max), key="trust_range")

    vel_min, vel_max = int(df.velocity_last_24h.min()), int(df.velocity_last_24h.max())
    velocity_range = st.slider("קצב עסקאות (24 ש')", vel_min, vel_max, (vel_min, vel_max), key="velocity_range")

    age_min, age_max = int(df.cardholder_age.min()), int(df.cardholder_age.max())
    age_range = st.slider("גיל בעל הכרטיס", age_min, age_max, (age_min, age_max), key="age_range")

    fraud_status = st.radio("סטטוס הונאה", ["הכל", "הונאה בלבד", "תקין בלבד"], key="fraud_status")

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
mask = (
    df.amount.between(amount_range[0], amount_range[1])
    & df.transaction_hour.between(hour_range[0], hour_range[1])
    & df.merchant_category.isin(categories)
    & df.device_trust_score.between(trust_range[0], trust_range[1])
    & df.velocity_last_24h.between(velocity_range[0], velocity_range[1])
    & df.cardholder_age.between(age_range[0], age_range[1])
)
if foreign_filter == "כן":
    mask &= df.foreign_transaction == 1
elif foreign_filter == "לא":
    mask &= df.foreign_transaction == 0
if mismatch_filter == "כן":
    mask &= df.location_mismatch == 1
elif mismatch_filter == "לא":
    mask &= df.location_mismatch == 0
if fraud_status == "הונאה בלבד":
    mask &= df.is_fraud == 1
elif fraud_status == "תקין בלבד":
    mask &= df.is_fraud == 0

fdf = df[mask]

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<div class="ops-header">
    <div>
        <div class="ops-title">🛰️ לוח בקרה — זיהוי הונאות בכרטיסי אשראי</div>
        <div class="ops-subtitle">CREDIT CARD FRAUD MONITORING SYSTEM</div>
    </div>
    <div class="ops-badge">● MONITORING</div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("סה\"כ עסקאות (מסוננות)", f"{len(fdf):,}")
with k2:
    st.metric("מספר הונאות", f"{int(fdf.is_fraud.sum()):,}")
with k3:
    rate = (fdf.is_fraud.mean() * 100) if len(fdf) else 0.0
    st.metric("אחוז הונאה", f"{rate:.2f}%")
with k4:
    at_risk = fdf.loc[fdf.is_fraud == 1, "amount"].sum()
    st.metric("סכום בסיכון ($)", f"{at_risk:,.2f}")

if len(fdf) == 0:
    st.warning("אין נתונים התואמים לפילטרים שנבחרו. נסה להרחיב את טווחי הסינון.")
    st.stop()

# ---------------------------------------------------------------------------
# Fraud rate by category + Fraud rate by hour
# ---------------------------------------------------------------------------
c1, c2 = st.columns([1.1, 1])

with c1:
    st.markdown('<div class="section-title">שיעור הונאה לפי קטגוריית עסק</div>', unsafe_allow_html=True)
    sort_option = st.selectbox("מיין לפי", ["שיעור הונאה", "נפח עסקאות"], key="cat_sort", label_visibility="collapsed")
    cat_stats = fdf.groupby("merchant_category").agg(total=("is_fraud", "size"), fraud=("is_fraud", "sum"))
    cat_stats["rate"] = (cat_stats["fraud"] / cat_stats["total"] * 100).fillna(0)
    cat_stats = cat_stats.sort_values("rate" if sort_option == "שיעור הונאה" else "total", ascending=False)
    fig = px.bar(
        cat_stats,
        x=cat_stats.index,
        y="rate",
        text=cat_stats["rate"].map(lambda v: f"{v:.1f}%"),
        labels={"x": "קטגוריה", "rate": "שיעור הונאה (%)"},
        color_discrete_sequence=[AMBER],
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(style_fig(fig), use_container_width=True)

with c2:
    st.markdown('<div class="section-title">שיעור הונאה לפי שעה ביום</div>', unsafe_allow_html=True)
    hour_stats = (
        fdf.groupby("transaction_hour")
        .agg(total=("is_fraud", "size"), fraud=("is_fraud", "sum"))
        .reindex(range(24), fill_value=0)
    )
    hour_stats["rate"] = (hour_stats["fraud"] / hour_stats["total"] * 100).fillna(0)
    fig = px.line(
        hour_stats,
        x=hour_stats.index,
        y="rate",
        markers=True,
        labels={"x": "שעה", "rate": "שיעור הונאה (%)"},
        color_discrete_sequence=[RED],
    )
    fig.update_traces(fill="tozeroy", fillcolor="rgba(255,59,59,0.1)")
    st.plotly_chart(style_fig(fig), use_container_width=True)

# ---------------------------------------------------------------------------
# Correlation with fraud
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="section-title">אילו מאפיינים הכי קשורים להונאה? (קורלציה)</div>',
    unsafe_allow_html=True,
)
corr = fdf[NUM_FEATURES + ["is_fraud"]].corr()["is_fraud"].drop("is_fraud").fillna(0)
corr = corr.sort_values(key=lambda s: s.abs(), ascending=True)
corr_df = pd.DataFrame(
    {
        "feature": [FEATURE_LABELS[f] for f in corr.index],
        "corr": corr.values,
    }
)
fig = px.bar(
    corr_df,
    x="corr",
    y="feature",
    orientation="h",
    labels={"corr": "מקדם קורלציה עם הונאה", "feature": ""},
)
fig.update_traces(marker_color=[RED if v > 0 else CYAN for v in corr_df["corr"]])
fig.update_layout(showlegend=False)
st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

# ---------------------------------------------------------------------------
# Distribution comparisons: fraud vs legit
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">השוואת התפלגויות: הונאה מול תקין</div>', unsafe_allow_html=True)
dist_cols = ["amount", "device_trust_score", "velocity_last_24h", "cardholder_age"]
grid = st.columns(2)
for i, col in enumerate(dist_cols):
    with grid[i % 2]:
        fig = px.histogram(
            fdf,
            x=col,
            color="status_label",
            barmode="overlay",
            opacity=0.65,
            histnorm="percent",
            color_discrete_map=COLOR_MAP,
            labels={col: FEATURE_LABELS[col], "status_label": "סטטוס"},
        )
        fig.update_layout(title=dict(text=FEATURE_LABELS[col], font=dict(size=13, color=MUTED)))
        st.plotly_chart(style_fig(fig, height=280), use_container_width=True)

# ---------------------------------------------------------------------------
# Interactive scatter explorer
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">חקירה חופשית: פיזור בין שני מאפיינים</div>', unsafe_allow_html=True)
sc1, sc2 = st.columns(2)
with sc1:
    x_feat = st.selectbox(
        "ציר X", NUM_FEATURES, index=NUM_FEATURES.index("device_trust_score"),
        format_func=lambda f: FEATURE_LABELS[f], key="scatter_x",
    )
with sc2:
    y_feat = st.selectbox(
        "ציר Y", NUM_FEATURES, index=NUM_FEATURES.index("velocity_last_24h"),
        format_func=lambda f: FEATURE_LABELS[f], key="scatter_y",
    )

fig = px.scatter(
    fdf,
    x=x_feat,
    y=y_feat,
    color="status_label",
    color_discrete_map=COLOR_MAP,
    opacity=0.7,
    labels={x_feat: FEATURE_LABELS[x_feat], y_feat: FEATURE_LABELS[y_feat], "status_label": "סטטוס"},
)
st.plotly_chart(style_fig(fig, height=420), use_container_width=True)

# ---------------------------------------------------------------------------
# Raw data table + download
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">טבלת עסקאות (ניתן למיין בלחיצה על כותרת עמודה)</div>', unsafe_allow_html=True)

table_df = fdf.copy()
table_df["סטטוס"] = table_df["is_fraud"].map({1: "🔴 הונאה", 0: "🟢 תקין"})
display_cols = [
    "transaction_id", "סטטוס", "amount", "transaction_hour", "merchant_category",
    "foreign_transaction", "location_mismatch", "device_trust_score",
    "velocity_last_24h", "cardholder_age",
]
st.dataframe(
    table_df[display_cols].rename(columns={
        "transaction_id": "מזהה עסקה",
        "amount": "סכום",
        "transaction_hour": "שעה",
        "merchant_category": "קטגוריה",
        "foreign_transaction": "בחו\"ל",
        "location_mismatch": "אי-התאמת מיקום",
        "device_trust_score": "אמון מכשיר",
        "velocity_last_24h": "קצב 24ש",
        "cardholder_age": "גיל",
    }),
    use_container_width=True,
    height=420,
)

st.download_button(
    "⬇ הורד נתונים מסוננים (CSV)",
    data=fdf.to_csv(index=False).encode("utf-8-sig"),
    file_name="filtered_transactions.csv",
    mime="text/csv",
)
