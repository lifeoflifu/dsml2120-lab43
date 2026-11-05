from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


APP_DIR = Path(__file__).parent
STAGES = {
    "sessions": "Sessions",
    "product_views": "Product views",
    "add_to_cart": "Add to cart",
    "checkouts": "Checkouts",
    "purchases": "Purchases",
}
REQUIRED_COLUMNS = ["date", "traffic_source", "device", *STAGES]
INDIGO = "#514786"
CORAL = "#964932"
INK = "#292333"
PAGE_COLORS = {
    "Summary": "#F8F0CF",
    "Funnel": "#FCDEC2",
    "Traffic sources": "#DDD6EC",
    "Devices": "#F9E7E9",
}


@st.cache_data
def load_data():
    raw = pd.read_csv(APP_DIR / "data" / "website_funnel.csv", parse_dates=["date"])
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
        margin=dict(l=8, r=60, t=12, b=52),
        font=dict(family="Arial, sans-serif", size=14, color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.update_xaxes(title=axis, rangemode="tozero", gridcolor="rgba(156,140,146,0.19)")
    return fig


def conversion_by(data, group):
    counts = data.groupby(group)[["sessions", "purchases"]].sum()
    # Pooled counts weight each visit equally, even when days have different traffic.
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
            INDIGO,
            [
                f"{group}<br>{row.purchases:,} purchases / {row.sessions:,} sessions"
                f"<br>{row.conversion:.2%} conversion"
                for group, row in rates.iterrows()
            ],
            "Purchase conversion (%)",
            280,
        )
        fig.update_xaxes(tickformat=".1%", range=[0, comparison_max])
        st.plotly_chart(fig, theme=None, config={"displayModeBar": False})
    st.caption(caption)


def funnel_insight():
    if largest_stage:
        return f"{transition} had the largest drop at **{loss[largest_stage]:.1%}**."
    return "There are no stage-to-stage percentages for this selection."


def source_insight():
    if source_rates.empty:
        return "There are no source conversion rates for this selection."
    leader = source_rates.index[0]
    rate = source_rates.iloc[0]["conversion"]
    if len(source_rates) == 1:
        return f"**{leader}** converted at **{rate:.2%}**. Select more sources to compare."
    return f"**{leader}** led the selected sources at **{rate:.2%}**."


def device_insight():
    if len(device_rates) == 2:
        desktop = device_rates.loc["Desktop", "conversion"]
        mobile = device_rates.loc["Mobile", "conversion"]
        return (
            f"Desktop converted at **{desktop:.2%}** and mobile at **{mobile:.2%}**, "
            f"a gap of **{abs(desktop - mobile) * 100:.2f} percentage points**."
        )
    if len(device_rates) == 1:
        return (
            f"**{device_rates.index[0]}** converted at "
            f"**{device_rates.iloc[0]['conversion']:.2%}**. Select all devices to compare."
        )
    return "There are no device conversion rates for this selection."


def show_funnel():
    with st.container(key="funnel_section"):
        st.subheader("Q1 · Where do visits drop off?")
        if largest_stage:
            highlight, takeaway = st.columns([1, 3], vertical_alignment="center")
            with highlight.container(key="funnel_highlight"):
                st.metric("Largest percentage drop", f"{loss[largest_stage]:.1%}")
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
            [CORAL if stage == largest_stage else INDIGO for stage in STAGES],
            [
                f"{STAGES[stage]}<br>{totals[stage]:,} reached this stage"
                + (f"<br>{loss[stage]:.1%} drop from previous stage" if pd.notna(loss[stage]) else "")
                for stage in STAGES
            ],
            "Count reaching each stage",
            290,
        )
        fig.update_xaxes(tickformat="~s")
        st.plotly_chart(fig, theme=None, config={"displayModeBar": False})
        st.caption("Each bar counts visits reaching a stage. Hover to see the percentage lost from the previous stage.")


def show_sources():
    with st.container(key="source_section"):
        st.subheader("Q2 · Which source converts best?")
        conversion_chart(
            source_rates,
            "Total purchases divided by total sessions for each selected traffic source.",
            comparison_max,
        )


def show_devices():
    with st.container(key="device_section"):
        st.subheader("Q3 · How do devices compare?")
        conversion_chart(
            device_rates,
            "Total purchases divided by total sessions for each selected device.",
            comparison_max,
        )


def summary():
    with st.container(key="summary_insights"):
        st.subheader("At a glance")
        st.markdown(f"**Funnel.** {funnel_insight()}")
        st.markdown(f"**Traffic sources.** {source_insight()}")
        st.markdown(f"**Devices.** {device_insight()}")
    show_funnel()
    sources_col, devices_col = st.columns(2)
    with sources_col:
        show_sources()
    with devices_col:
        show_devices()


def funnel():
    st.write(funnel_insight())
    show_funnel()


def traffic_sources():
    st.markdown(source_insight())
    show_sources()


def devices():
    st.markdown(device_insight())
    show_devices()


# Shared navigation and filters stay in the entrypoint so selections persist across pages.
st.set_page_config(page_title="From Visit to Purchase", page_icon="🛒", layout="wide")
page = st.navigation(
    [
        st.Page(summary, title="Summary", default=True),
        st.Page(funnel, title="Funnel", url_path="funnel"),
        st.Page(traffic_sources, title="Traffic sources", url_path="sources"),
        st.Page(devices, title="Devices", url_path="devices"),
    ],
    position="top",
)
style = (APP_DIR / "style.css").read_text().replace("PAGE_CANVAS", PAGE_COLORS[page.title])
st.html(f"<style>{style}</style>")
st.html(
    '<header class="visit-header">'
    '<div><p class="eyebrow">DSML 2120 · Lab 4.3 · Lifu Deng</p>'
    '<h1>From visit to <em>purchase.</em></h1>'
    '<p class="description">A weekly view of where visits drop off, '
    'which sources convert, and how devices compare.</p></div>'
    '<div class="visit-mark" aria-hidden="true">vp</div></header>'
    f'<p class="view-label">{page.title} / Website funnel</p>'
)

data, dropped = load_data()
first = data["date"].min().date()
last = data["date"].max().date()
sources = sorted(data["traffic_source"].unique())
with st.sidebar:
    st.header("Refine the view")
    dates = st.date_input("Date range", (first, last), min_value=first, max_value=last, key="dates")
    selected_sources = st.multiselect("Traffic source", sources, default=sources, key="sources")
    device = st.selectbox("Device", ["All devices", *sorted(data["device"].unique())], key="device")
    st.caption("Your selections carry across every page.")
    st.caption(
        "Synthetic course data · website_funnel.csv. "
        "Rows missing a date, source, device, or funnel count are excluded "
        f"({dropped:,} removed)."
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

# All pages use the same filtered totals and weighted conversion calculations.
totals = filtered[list(STAGES)].sum()
sessions, purchases = totals["sessions"], totals["purchases"]
conversion = f"{purchases / sessions:.2%}" if sessions else "No data"
with st.container(key="kpi_row"):
    for column, label, value in zip(
        st.columns(3),
        ["Sessions", "Purchases", "Purchase conversion"],
        [f"{sessions:,}", f"{purchases:,}", conversion],
    ):
        column.metric(label, value)
st.caption(f"{start:%b %d, %Y} to {end:%b %d, %Y} · {len(filtered):,} daily source/device rows")

previous = totals.shift()
loss = (previous - totals) / previous.where(previous > 0)
largest = loss.dropna()
largest_stage = largest.idxmax() if not largest.empty else None
transition = ""
if largest_stage:
    position = list(STAGES).index(largest_stage)
    transition = f"{list(STAGES.values())[position - 1]} → {STAGES[largest_stage].lower()}"
source_rates = conversion_by(filtered, "traffic_source")
device_rates = conversion_by(filtered, "device")
# Keep the two rate charts on the same scale so their bar lengths can be compared.
comparison_max = max([0.05, *source_rates["conversion"], *device_rates["conversion"]]) * 1.12
page.run()
