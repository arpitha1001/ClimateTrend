"""
app.py - Streamlit interface for ClimateTrend.

All maths lives in climate_analysis.py; this file only handles layout,
user input and plotting.

Run with:  streamlit run app.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

import climate_analysis as ca

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "GLB.Ts+dSST.csv")
NASA_URL = "https://data.giss.nasa.gov/gistemp/data_v4.html"
NASA_CSV = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"

# Consistent visual language for the three kinds of values
C_OBS, C_INT, C_EXT = "#1f5fa8", "#1a9850", "#d73027"

st.set_page_config(page_title="ClimateTrend", page_icon="🌡️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2rem;}
h1, h2, h3 {color: #14355e;}
.legend-chip {display:inline-block; padding:2px 10px; border-radius:12px;
              color:white; font-size:0.85rem; margin-right:6px;}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def init_state():
    st.session_state.setdefault("df", None)
    st.session_state.setdefault("source_name", None)
    st.session_state.setdefault("interps", [])   # list[InterpolationResult]
    st.session_state.setdefault("extraps", [])   # list[ExtrapolationResult]


def legend_chips():
    st.markdown(
        f'<span class="legend-chip" style="background:{C_OBS}">Observed (NASA)</span>'
        f'<span class="legend-chip" style="background:{C_INT}">Interpolated estimate</span>'
        f'<span class="legend-chip" style="background:{C_EXT}">Extrapolated estimate</span>',
        unsafe_allow_html=True)


def require_data():
    """Stop the page with a friendly message if no dataset is loaded."""
    if st.session_state["df"] is None:
        st.warning("No dataset loaded yet. Go to the **Data** page and upload "
                   "the NASA GISTEMP CSV (or tick the option to load it from the data/ folder).")
        st.stop()
    return st.session_state["df"]


def current_series(df):
    """Annual series for the column chosen in the sidebar."""
    try:
        return ca.get_series(df, st.session_state.get("column", "J-D"))
    except ca.ValidationError as exc:
        st.error(str(exc))
        st.stop()


def style_axes(ax, title):
    ax.set_title(title, fontsize=12, color="#14355e")
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Temperature anomaly ({chr(176)}C vs {ca.BASELINE_TEXT})")
    ax.grid(alpha=0.3)
    ax.axhline(0, color="grey", lw=0.8)


def show(fig):
    st.pyplot(fig)
    plt.close(fig)


def plot_observed(ax, s, label="Observed (NASA GISTEMP)"):
    ax.plot(s["Year"], s["Anomaly"], "-o", color=C_OBS, ms=3, lw=1.3, label=label)


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_home():
    st.title("🌡️ ClimateTrend")
    st.caption("Interpolation, Extrapolation and Climate Change - "
               "Mini-Project, Topic 8")

    st.header("Problem statement")
    st.write(
        "Develop an interactive Python application that uses historical global "
        "temperature anomaly data to demonstrate the mathematical concepts of "
        "**interpolation** and **extrapolation** in the context of climate change. "
        "The application lets users visualise historical temperature trends, "
        "estimate values *between* observed data points (interpolation), and explore "
        "mathematical estimates *beyond* the observed data range (extrapolation), "
        "while explaining the limitations of these estimates.")

    st.header("Objectives")
    st.markdown("""
1. Load and clean the official NASA GISS global temperature dataset (GISTEMP v4).
2. Visualise the historical temperature-anomaly trend.
3. Apply **linear interpolation** to estimate values between observed years
   (including years with missing data).
4. Apply **linear extrapolation** to estimate values beyond the last observed year.
5. Summarise the long-term trend (slope, warmest/coldest years, decade averages).
6. Compare observed values, interpolated estimates and extrapolated estimates on one graph.
7. Explain why simple extrapolation is **not** a reliable climate forecast.
""")

    st.header("About the data")
    st.markdown(f"""
* **Source:** NASA GISS Surface Temperature Analysis (GISTEMP v4) - [{NASA_URL}]({NASA_URL})
* **File expected:** `GLB.Ts+dSST.csv` (global-mean monthly, seasonal and annual means)
* **Quantity:** temperature **anomaly**, i.e. the difference from a reference level, **not** absolute temperature
* **Units:** {ca.UNITS_TEXT}
* **Reference baseline:** {ca.BASELINE_TEXT}
* **Annual columns:** `J-D` (January-December mean) and `D-N` (December-November mean)
* **Missing values:** written as `***` in the file
* This app does not bundle any data - everything you see comes from the file you load.
""")
    legend_chips()
    st.info("Start on the **Data** page in the sidebar to load the dataset.")


def page_data():
    st.header("Data: load the NASA GISTEMP dataset")
    st.markdown(f"Download `GLB.Ts+dSST.csv` from [{NASA_URL}]({NASA_URL}) "
                f"(direct link: [{NASA_CSV}]({NASA_CSV})), then upload it below.")

    up = st.file_uploader("Upload GLB.Ts+dSST.csv", type=["csv"])
    use_default = False
    if os.path.exists(DEFAULT_PATH):
        use_default = st.checkbox("Load data/GLB.Ts+dSST.csv from the project folder")

    if up is not None:
        try:
            st.session_state["df"] = ca.load_giss_csv(up)
            st.session_state["source_name"] = up.name
            st.session_state["interps"], st.session_state["extraps"] = [], []
            st.success(f"Loaded **{up.name}** successfully.")
        except ca.ValidationError as exc:
            st.error(f"Could not load file: {exc}")
        except Exception as exc:  # unexpected parsing problem
            st.error(f"Unexpected error while reading the file: {exc}")
    elif use_default:
        try:
            st.session_state["df"] = ca.load_giss_csv(DEFAULT_PATH)
            st.session_state["source_name"] = "data/GLB.Ts+dSST.csv"
        except ca.ValidationError as exc:
            st.error(f"Could not load file: {exc}")

    df = st.session_state["df"]
    if df is None:
        st.info("No file loaded yet. The rest of the app unlocks once a valid file is loaded.")
        return

    s = current_series(df)
    st.subheader("Dataset summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Source file", st.session_state["source_name"])
    c2.metric("Years in file", f"{int(df.Year.min())}-{int(df.Year.max())}")
    c3.metric("Valid annual values", len(s))
    miss = ca.missing_report(df, st.session_state["column"])
    c4.metric("Missing annual values", len(miss))
    st.caption(f"Units: {ca.UNITS_TEXT}; baseline: {ca.BASELINE_TEXT}. "
               f"Annual column in use: **{st.session_state['column']}**.")

    if len(miss):
        st.warning("Years with a missing annual value (these are skipped in the maths; "
                   "interpolation can estimate them): "
                   + ", ".join(str(int(y)) for y in miss["Year"]))

    st.subheader("Temperature trend graph")
    fig, ax = plt.subplots(figsize=(10, 4.2))
    plot_observed(ax, s)
    style_axes(ax, "Global temperature anomaly (observed)")
    ax.legend()
    show(fig)

    st.subheader("Historical data table")
    lo, hi = int(df.Year.min()), int(df.Year.max())
    yr_range = st.slider("Year range", lo, hi, (lo, hi))
    view_all = st.checkbox("Show all monthly/seasonal columns", value=False)
    cols = list(df.columns) if view_all else ["Year", st.session_state["column"]]
    shown = df[(df.Year >= yr_range[0]) & (df.Year <= yr_range[1])][cols]
    st.dataframe(shown, use_container_width=True, hide_index=True)


def page_interpolation():
    st.header("Linear interpolation")
    df = require_data()
    s = current_series(df)
    lo, hi = int(s.Year.min()), int(s.Year.max())

    st.markdown("**Interpolation** estimates a value *between* two known observations. "
                "For a year $x$ between known years $x_0$ and $x_1$:")
    st.latex(r"y = y_0 + (y_1 - y_0)\,\frac{x - x_0}{x_1 - x_0}")
    st.caption(f"Valid years: {lo} to {hi} (inside the observed range).")

    txt = st.text_input("Year to estimate", value="", placeholder=f"e.g. {lo + (hi - lo) // 2}",
                        key="interp_year")
    if st.button("Calculate interpolation", type="primary"):
        try:
            res = ca.interpolate_at(s, txt)
            st.session_state["interp_last"] = res
            if not res.is_observed and not any(r.year == res.year for r in st.session_state["interps"]):
                st.session_state["interps"].append(res)
        except ca.ValidationError as exc:
            st.session_state.pop("interp_last", None)
            st.error(str(exc))

    res = st.session_state.get("interp_last")
    if res is not None:
        if res.is_observed:
            st.info(f"{res.year:g} is an observed year: NASA value = **{res.value:.3f} {chr(176)}C**. "
                    "Nothing to interpolate; choose a year with no value (or a fractional year such as 1990.5).")
        else:
            st.subheader("Calculation")
            st.latex(rf"y = {res.y0:.3f} + ({res.y1:.3f} - {res.y0:.3f})"
                     rf"\times\frac{{{res.year:g} - {res.x0:g}}}{{{res.x1:g} - {res.x0:g}}}"
                     rf" = {res.value:.3f}")
            st.success(f"Interpolated anomaly for {res.year:g}: **{res.value:.3f} {chr(176)}C** "
                       f"(relative to {ca.BASELINE_TEXT}). This is an estimate, not an observation.")
            fig, ax = plt.subplots(figsize=(8, 3.8))
            pad = max(5, int(res.x1 - res.x0) * 2)
            near = s[(s.Year >= res.x0 - pad) & (s.Year <= res.x1 + pad)]
            ax.plot(near["Year"], near["Anomaly"], "-o", color=C_OBS, ms=4, label="Observed")
            ax.plot([res.x0, res.x1], [res.y0, res.y1], "--", color=C_INT, lw=1.2,
                    label="Interpolating line")
            ax.plot(res.year, res.value, "D", color=C_INT, ms=9, label="Interpolated estimate")
            ax.plot([res.x0, res.x1], [res.y0, res.y1], "o", color=C_OBS, ms=8, mfc="white",
                    label="Points used")
            style_axes(ax, f"Interpolation at {res.year:g}")
            ax.legend()
            show(fig)

    st.subheader("Fill missing years")
    fills = ca.fill_missing_years(df, st.session_state["column"])
    if fills.empty:
        st.write("No missing years inside the data range for this column.")
    else:
        st.write("Years in the file with no value, estimated by interpolation:")
        show_df = fills.rename(columns={"Anomaly": "Interpolated anomaly (deg C)"})
        st.dataframe(show_df, hide_index=True)
        if st.button("Add all of these to the comparison graph"):
            have = {r.year for r in st.session_state["interps"]}
            for yr in fills["Year"]:
                if float(yr) not in have:
                    st.session_state["interps"].append(ca.interpolate_at(s, yr))
            st.success("Added.")

    st.caption(f"Saved interpolated estimates: {len(st.session_state['interps'])}")


def page_extrapolation():
    st.header("Linear extrapolation")
    df = require_data()
    s = current_series(df)
    last = int(s.Year.max())

    st.error("**Warning:** extrapolation extends a pattern *beyond* the data. "
             "A straight line cannot capture changing emissions, feedbacks, volcanic "
             "eruptions, El Nino/La Nina or policy. **It is not a climate forecast.** "
             "Real projections use physics-based climate models.")
    st.markdown("Two simple methods are offered:")
    st.markdown("* **Two-point line:** the line through the last two observations "
                "(very sensitive to year-to-year noise).\n"
                "* **Least-squares trend:** the best-fit straight line "
                "$y = a + b\\,x$ over the last *N* years.")
    st.latex(r"b = \frac{\sum (x_i-\bar x)(y_i-\bar y)}{\sum (x_i-\bar x)^2},\qquad "
             r"a = \bar y - b\,\bar x,\qquad \hat y(x)=a+b\,x")

    c1, c2, c3 = st.columns(3)
    txt = c1.text_input("Future year to estimate", placeholder=f"e.g. {last + 10}", key="ext_year")
    method = c2.selectbox("Method", ca.METHODS, index=1)
    max_w = max(6, min(60, len(s)))
    window = c3.slider("Window N (years, least-squares only)", 5, max_w, min(30, max_w),
                       disabled=(method == ca.METHOD_TWO_POINT))

    if st.button("Calculate extrapolation", type="primary"):
        try:
            r = ca.extrapolate_at(s, txt, method, window)
            st.session_state["extrap_last"] = r
            if not any(e.year == r.year and e.method == r.method and e.based_on == r.based_on
                       for e in st.session_state["extraps"]):
                st.session_state["extraps"].append(r)
        except ca.ValidationError as exc:
            st.session_state.pop("extrap_last", None)
            st.error(str(exc))

    r = st.session_state.get("extrap_last")
    if r is not None:
        st.subheader("Result")
        st.latex(rf"\hat y({r.year:g}) = {r.intercept:.3f} + ({r.slope:.5f}) \times {r.year:g}"
                 rf" = {r.value:.3f}")
        st.warning(f"Extrapolated anomaly for {r.year:g}: **{r.value:.2f} {chr(176)}C** "
                   f"({r.horizon_years:g} years beyond the data; method: {r.method}; "
                   f"based on {r.based_on}; slope = {r.slope * 10:.3f} {chr(176)}C per decade). "
                   "Treat as a mathematical estimate, not a prediction.")
        if r.horizon_years > 30:
            st.caption("The further beyond the data, the less trustworthy a straight-line estimate becomes.")

        fig, ax = plt.subplots(figsize=(10, 4.2))
        plot_observed(ax, s)
        xs = np.array([last, r.year])
        ax.plot(xs, r.intercept + r.slope * xs, "--", color=C_EXT, lw=1.5, label="Extrapolated line")
        ax.plot(r.year, r.value, "^", color=C_EXT, ms=10, label="Extrapolated estimate")
        style_axes(ax, "Extrapolation beyond the observed range")
        ax.legend()
        show(fig)

    st.subheader("Back-test: how well does extrapolation work on years we already know?")
    st.write("Hide the most recent years, extrapolate them using only the earlier data, "
             "then compare with the real NASA values.")
    hold = st.slider("Years to hide", 3, 30, 10)
    try:
        bt = ca.backtest_extrapolation(s, hold, method, window)
        fig, ax = plt.subplots(figsize=(10, 3.8))
        train = s[s.Year < bt.Year.min()]
        ax.plot(train["Year"], train["Anomaly"], "-o", color=C_OBS, ms=3, lw=1, label="Observed (used)")
        ax.plot(bt["Year"], bt["Observed"], "-o", color=C_OBS, ms=4, mfc="white", label="Observed (hidden)")
        ax.plot(bt["Year"], bt["Extrapolated"], "--^", color=C_EXT, ms=5, label="Extrapolated")
        style_axes(ax, f"Back-test, last {hold} years hidden")
        ax.set_xlim(bt.Year.min() - 30, bt.Year.max() + 2)
        ax.legend()
        show(fig)
        m1, m2 = st.columns(2)
        m1.metric("Mean absolute error", f"{bt['Error'].abs().mean():.3f} {chr(176)}C")
        m2.metric("Error in final year", f"{bt['Error'].iloc[-1]:+.3f} {chr(176)}C")
        st.dataframe(bt.round(3), hide_index=True)
    except ca.ValidationError as exc:
        st.info(str(exc))

    st.caption(f"Saved extrapolated estimates: {len(st.session_state['extraps'])}")


def page_trend():
    st.header("Trend analysis")
    df = require_data()
    s = current_series(df)
    summ = ca.trend_summary(s)
    deg = chr(176)

    c1, c2, c3 = st.columns(3)
    c1.metric("Warmest year", f"{summ['warmest_year']}", f"{summ['warmest_value']:+.2f} {deg}C")
    c2.metric("Coldest year", f"{summ['coldest_year']}", f"{summ['coldest_value']:+.2f} {deg}C")
    c3.metric("Whole-record trend", f"{summ['full_slope_per_decade']:+.3f} {deg}C / decade")
    if "recent_slope_per_decade" in summ:
        st.write(f"Trend over the most recent 30 years ({summ['recent_start']}-{summ['last_year']}): "
                 f"**{summ['recent_slope_per_decade']:+.3f} {deg}C per decade** "
                 f"(R² = {summ['recent_r2']:.2f}). Compare with the whole record: "
                 f"{summ['full_slope_per_decade']:+.3f} {deg}C per decade "
                 f"(R² = {summ['full_r2']:.2f}). The slope depends on the period chosen.")

    st.subheader("Choose a period for the straight-line fit")
    lo, hi = summ["first_year"], summ["last_year"]
    a, b = st.slider("Period", lo, hi, (max(lo, hi - 49), hi))
    try:
        fit = ca.fit_linear_trend(s, a, b)
        fig, ax = plt.subplots(figsize=(10, 4.2))
        plot_observed(ax, s)
        xs = np.array([fit.start_year, fit.end_year])
        ax.plot(xs, fit.predict(xs), "-", color="#ff7f00", lw=2.5,
                label=f"Linear fit {fit.start_year}-{fit.end_year}")
        style_axes(ax, "Observed data with linear trend")
        ax.legend()
        show(fig)
        st.write(f"Slope = **{fit.slope * 10:+.3f} {deg}C per decade**, "
                 f"R² = {fit.r_squared:.2f}, based on {fit.n_points} values.")
    except ca.ValidationError as exc:
        st.error(str(exc))

    st.subheader("Decade averages")
    dec = ca.decade_averages(s)
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.bar(dec["Decade"].astype(str) + "s", dec["Mean anomaly (deg C)"],
           color=[C_OBS if v >= 0 else "#6baed6" for v in dec["Mean anomaly (deg C)"]])
    ax.set_ylabel(f"Mean anomaly ({deg}C)")
    ax.set_title("Mean anomaly by decade", color="#14355e")
    ax.axhline(0, color="grey", lw=0.8)
    plt.setp(ax.get_xticklabels(), rotation=60, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    show(fig)
    st.dataframe(dec.round(3), hide_index=True)
    st.caption("Decades at the start or end of the file may contain fewer than 10 years.")


def page_compare():
    st.header("Comparison graph and downloads")
    df = require_data()
    s = current_series(df)
    interps, extraps = st.session_state["interps"], st.session_state["extraps"]
    legend_chips()

    if not interps and not extraps:
        st.info("No estimates saved yet. Calculate some on the Interpolation and "
                "Extrapolation pages and they will appear here.")

    fig, ax = plt.subplots(figsize=(11, 4.6))
    plot_observed(ax, s)
    ipts = [r for r in interps if not r.is_observed]
    if ipts:
        ax.plot([r.year for r in ipts], [r.value for r in ipts], "D", color=C_INT, ms=8,
                label="Interpolated estimates")
    if extraps:
        last_obs = s.iloc[-1]
        for method in sorted({e.method for e in extraps}):
            grp = sorted([e for e in extraps if e.method == method], key=lambda e: e.year)
            ls = "--" if method == ca.METHOD_TREND else ":"
            ax.plot([last_obs.Year] + [e.year for e in grp],
                    [last_obs.Anomaly] + [e.value for e in grp],
                    ls, color=C_EXT, lw=1.2, alpha=0.7)
            ax.plot([e.year for e in grp], [e.value for e in grp], "^", color=C_EXT, ms=9,
                    label=f"Extrapolated: {method}")
    style_axes(ax, "Observed vs interpolated vs extrapolated")
    ax.legend(fontsize=8)
    show(fig)
    st.caption("Extrapolated points are mathematical estimates only, not forecasts.")

    results = ca.build_results_table(s, interps, extraps)
    st.subheader("Results table")
    st.dataframe(results, use_container_width=True, hide_index=True)

    d1, d2 = st.columns(2)
    d1.download_button("⬇ Download results (observed + estimates) as CSV",
                       results.to_csv(index=False).encode("utf-8"),
                       file_name="climatetrend_results.csv", mime="text/csv")
    processed = s.rename(columns={"Anomaly": "Anomaly_degC_vs_1951-1980"})
    d2.download_button("⬇ Download cleaned annual data as CSV",
                       processed.to_csv(index=False).encode("utf-8"),
                       file_name="climatetrend_annual_clean.csv", mime="text/csv")

    if st.button("Clear saved estimates"):
        st.session_state["interps"], st.session_state["extraps"] = [], []
        st.rerun()


def page_how():
    st.header("Limitations and how the app works")
    st.markdown(f"""
**How it works**
1. `climate_analysis.py` reads the NASA CSV, skips the title line, finds the `Year,...` header and converts `***` to missing values.
2. It builds an annual series (Year, anomaly in {chr(176)}C vs {ca.BASELINE_TEXT}) using the annual column you pick in the sidebar.
3. *Interpolation* finds the nearest valid observations either side of your year and applies the straight-line formula.
4. *Extrapolation* fits a straight line (last two points, or least squares over the last N years) and extends it past the final year.
5. `app.py` shows the results, plots them in distinct colours and lets you download everything as CSV.

**Limitations**
* **Linear interpolation** assumes the change between two known years is a straight line; real year-to-year values fluctuate, so it is only an estimate.
* **Extrapolation** assumes the recent trend simply continues. Climate is driven by emissions, feedbacks, ocean cycles, volcanoes and policy, none of which a straight line represents.
* The estimate gets less reliable the farther it is from the data, and the choice of window or end points changes the answer (see the back-test).
* Anomalies are relative to {ca.BASELINE_TEXT}, not absolute temperatures.
* Official climate projections come from physics-based climate models and scenarios, **not** from curve fitting.
""")


# ----------------------------------------------------------------------------
# Main: sidebar navigation
# ----------------------------------------------------------------------------
def main():
    init_state()
    st.sidebar.title("🌡️ ClimateTrend")
    page = st.sidebar.radio("Navigate", [
        "Home", "Data", "Interpolation", "Extrapolation",
        "Trend analysis", "Comparison & download", "Limitations"])

    df = st.session_state["df"]
    if df is not None:
        avail = [c for c in ca.ANNUAL_COLUMNS if c in df.columns]
        st.session_state["column"] = st.sidebar.selectbox(
            "Annual column", avail,
            help="J-D = Jan-Dec mean; D-N = Dec(previous year)-Nov mean.")
        st.sidebar.success(f"Loaded: {st.session_state['source_name']}")
    else:
        st.session_state["column"] = "J-D"
        st.sidebar.warning("No dataset loaded")
    st.sidebar.caption(f"Units: {ca.UNITS_TEXT}\n\nBaseline: {ca.BASELINE_TEXT}")

    {"Home": page_home, "Data": page_data, "Interpolation": page_interpolation,
     "Extrapolation": page_extrapolation, "Trend analysis": page_trend,
     "Comparison & download": page_compare, "Limitations": page_how}[page]()


main()
