from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


DATA_FILE = Path(__file__).parent / "data" / "website_funnel.csv"
STAGES = {
    "sessions": "Sessions",
    "product_views": "Product views",
    "add_to_cart": "Add to cart",
    "checkouts": "Checkouts",
    "purchases": "Purchases",
}
REQUIRED_COLUMNS = ["date", "traffic_source", "device", *STAGES]
VIOLET = "#5143A3"
CORAL = "#A83E37"
INK = "#231E3E"


@st.cache_data
def load_data():
    raw = pd.read_csv(DATA_FILE, parse_dates=["date"])
    clean = raw.dropna(subset=REQUIRED_COLUMNS)
    return clean, len(raw) - len(clean)


def horizontal_bars(labels, values, text, colors, hover, axis, height):
    fig = go.Figure(
        go.Bar(
            y=list(labels),
            x=list(values),
            text=text,
            orientation="h",
            marker_color=colors,
            textposition="outside",
            cliponaxis=False,
            customdata=hover,
            hovertemplate="%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=44, t=12, b=52),
        font=dict(size=14, color=INK),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.update_xaxes(title=axis, rangemode="tozero", gridcolor="#E9E5F0")
    return fig


def conversion_by(data, group):
    counts = data.groupby(group)[["sessions", "purchases"]].sum()
    # Use pooled counts so a small day does not carry the same weight as a large day.
    rates = counts.loc[counts["sessions"] > 0].copy()
    rates["conversion"] = rates["purchases"] / rates["sessions"]
    return rates.sort_values("conversion", ascending=False)


def conversion_chart(rates, caption, comparison_max):
    if rates.empty:
        st.info("Conversion needs at least one session.")
    else:
        fig = horizontal_bars(
            rates.index,
            rates["conversion"],
            [f"{rate:.2%}" for rate in rates["conversion"]],
            VIOLET,
            [
                f"{group}<br>{row.purchases:,} purchases / {row.sessions:,} sessions"
                f"<br>{row.conversion:.2%} conversion"
                for group, row in rates.iterrows()
            ],
            "Purchase conversion (%)",
            242,
        )
        fig.update_xaxes(tickformat=".1%", range=[0, comparison_max])
        st.plotly_chart(fig, theme=None, config={"displayModeBar": False})
    st.caption(caption)


st.set_page_config(page_title="From Visit to Purchase", page_icon="🛒", layout="wide")
st.html("""
<style>
.funnel-hero {background:#231e3e;color:white;border-radius:18px;padding:1.45rem 1.7rem;}
.funnel-hero h1 {color:white;margin:0;padding:.15rem 0 .3rem;font-size:clamp(1.9rem,4vw,3.2rem);}
.funnel-hero p {margin:0;color:#f4efff;}
.funnel-hero .eyebrow {color:#ffe191;font-size:.84rem;font-weight:700;letter-spacing:.06em;}
.funnel-palette {display:flex;gap:.35rem;margin-top:.75rem;}
.funnel-palette span {width:2rem;height:.32rem;border-radius:.4rem;}
.st-key-metric_sessions [data-testid="stMetric"],
.st-key-metric_purchases [data-testid="stMetric"],
.st-key-metric_conversion [data-testid="stMetric"],
.st-key-funnel_highlight [data-testid="stMetric"] {border-radius:14px;padding:.8rem 1rem;color:#231e3e;}
.st-key-metric_sessions [data-testid="stMetric"] {background:#fff0b3;}
.st-key-metric_purchases [data-testid="stMetric"] {background:#ffded1;}
.st-key-metric_conversion [data-testid="stMetric"] {background:#d8f3e9;}
.st-key-funnel_highlight [data-testid="stMetric"] {background:#ffded1;}
</style>
<header class="funnel-hero">
<p class="eyebrow">DSML 2120 · LAB 4.3 · E-COMMERCE</p>
<h1>From Visit to Purchase</h1>
<p>See where shoppers drop off and which sources or devices to investigate.</p>
<div class="funnel-palette" aria-hidden="true">
<span style="background:#f7d765"></span><span style="background:#f4a089"></span>
<span style="background:#a79af0"></span><span style="background:#7ed0bd"></span>
</div>
</header>
""")

# Load the class data and use the same filtered rows for every chart and KPI.
data, dropped = load_data()
first = data["date"].min().date()
last = data["date"].max().date()
sources = sorted(data["traffic_source"].unique())

with st.sidebar:
    st.header("Filters")
    dates = st.date_input("Date range", (first, last), min_value=first, max_value=last)
    selected_sources = st.multiselect("Traffic source", sources, default=sources)
    device = st.selectbox("Device", ["All devices", *sorted(data["device"].unique())])
    st.caption("Filters update the KPIs, charts, and insights.")

st.caption(
    "Synthetic course data · website_funnel.csv · Rows with missing dates, sources, "
    f"devices, or funnel counts are excluded ({dropped:,} removed)."
)
if len(dates) != 2:
    st.info("Choose a start and end date to see results.")
    st.stop()

start, end = dates
filtered = data[
    data["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    & data["traffic_source"].isin(selected_sources)
]
if device != "All devices":
    filtered = filtered[filtered["device"] == device]
if filtered.empty:
    st.warning("No data for these filters. Choose a traffic source or broaden the date range.")
    st.stop()

st.caption(f"{start:%b %d, %Y} to {end:%b %d, %Y} · {len(filtered):,} daily source/device rows")
totals = filtered[list(STAGES)].sum()
sessions, purchases = totals["sessions"], totals["purchases"]
conversion = f"{purchases / sessions:.2%}" if sessions else "No data"
for column, key, label, value in zip(
    st.columns(3),
    ["metric_sessions", "metric_purchases", "metric_conversion"],
    ["Sessions", "Purchases", "Purchase conversion"],
    [f"{sessions:,}", f"{purchases:,}", conversion],
):
    with column.container(key=key):
        st.metric(label, value)

# Compare each step with the one immediately before it.
previous = totals.shift()
loss = (previous - totals) / previous.where(previous > 0)
largest = loss.dropna()
largest_stage = largest.idxmax() if not largest.empty else None
transition = ""
if largest_stage:
    position = list(STAGES).index(largest_stage)
    transition = f"{list(STAGES.values())[position - 1]} → {STAGES[largest_stage].lower()}"

with st.container(border=True):
    st.subheader("Q1 · Where is the largest percentage drop-off?")
    if largest_stage:
        highlight, takeaway = st.columns([1, 3], vertical_alignment="center")
        with highlight.container(key="funnel_highlight"):
            st.metric("Largest drop", f"{loss[largest_stage]:.1%}")
        with takeaway:
            st.markdown(f"**{transition}**")
            if largest_stage == "add_to_cart":
                st.write(
                    "Walk through the product page as a shopper. "
                    "Is the layout clean, and is the Add to Cart button easy to find and use?"
                )

    fig = horizontal_bars(
        STAGES.values(),
        totals,
        [f"{value:,}" for value in totals],
        [CORAL if stage == largest_stage else VIOLET for stage in STAGES],
        [
            f"{STAGES[stage]}<br>{totals[stage]:,} reached this stage"
            + (f"<br>{loss[stage]:.1%} drop from previous stage" if pd.notna(loss[stage]) else "")
            for stage in STAGES
        ],
        "Count reaching each stage",
        268,
    )
    fig.update_xaxes(tickformat="~s")
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})
    st.caption("Each bar shows how many reached a stage. Hover to see the drop-off from the previous stage.")

source_rates = conversion_by(filtered, "traffic_source")
device_rates = conversion_by(filtered, "device")
# The same scale makes bar lengths comparable across the two views.
comparison_max = max([0.05, *source_rates["conversion"], *device_rates["conversion"]]) * 1.12
source_col, device_col = st.columns(2)
with source_col.container(border=True):
    st.subheader("Q2 · Which source converts best?")
    conversion_chart(source_rates, "Total purchases divided by total sessions for each selected traffic source.", comparison_max)
with device_col.container(border=True):
    st.subheader("Q3 · How do devices compare?")
    conversion_chart(device_rates, "Total purchases divided by total sessions for each selected device.", comparison_max)

with st.container(border=True):
    st.subheader("Insights")
    if largest_stage:
        st.markdown(f"**Q1.** {transition} had the largest drop at **{loss[largest_stage]:.1%}**.")
    else:
        st.markdown("**Q1.** There are no stage-to-stage percentages for this selection.")
    if len(source_rates) > 1:
        leader = source_rates.index[0]
        st.markdown(f"**Q2.** **{leader}** led the selected sources at **{source_rates.loc[leader, 'conversion']:.2%}**.")
    elif len(source_rates) == 1:
        st.markdown(f"**Q2.** **{source_rates.index[0]}** converted at **{source_rates.iloc[0]['conversion']:.2%}**. Select more sources to compare.")
    else:
        st.markdown("**Q2.** There are no source conversion rates for this selection.")
    if len(device_rates) == 2:
        desktop = device_rates.loc["Desktop", "conversion"]
        mobile = device_rates.loc["Mobile", "conversion"]
        st.markdown(f"**Q3.** Desktop converted at **{desktop:.2%}** and mobile at **{mobile:.2%}**, a gap of **{abs(desktop - mobile) * 100:.2f} percentage points**.")
    elif len(device_rates) == 1:
        st.markdown(f"**Q3.** **{device_rates.index[0]}** converted at **{device_rates.iloc[0]['conversion']:.2%}**. Select all devices to compare.")
    else:
        st.markdown("**Q3.** There are no device conversion rates for this selection.")
