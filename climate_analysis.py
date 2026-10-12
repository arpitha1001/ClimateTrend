"""
climate_analysis.py - maths and data handling for ClimateTrend (no Streamlit here).

NASA GISTEMP v4 CSV facts used by this module
---------------------------------------------
* File: GLB.Ts+dSST.csv (Global-mean monthly, seasonal and annual means).
* Line 1 is a title ("Land-Ocean: Global Means"); line 2 is the header:
  Year,Jan,...,Dec,J-D,D-N,DJF,MAM,JJA,SON
* Values are temperature ANOMALIES in degrees Celsius (deg C), relative to the
  1951-1980 base period average. They are NOT absolute temperatures.
* Missing values are written as "***".
* J-D = January-December annual mean, D-N = December-November annual mean.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import pandas as pd

BASELINE_TEXT = "1951-1980 average"
UNITS_TEXT = "degrees Celsius (deg C) anomaly"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ANNUAL_COLUMNS = ["J-D", "D-N"]


class ValidationError(ValueError):
    """Raised with a user-friendly message when input is invalid."""


# ----------------------------------------------------------------------------
# 1. Loading and cleaning
# ----------------------------------------------------------------------------
def load_giss_csv(source: Union[str, bytes, io.IOBase]) -> pd.DataFrame:
    """Read a NASA GISTEMP CSV (path, bytes, or file-like) into a DataFrame.

    Returns a DataFrame with a 'Year' column (int) and numeric columns for
    each month / annual / seasonal column. '***' becomes NaN.
    """
    if source is None:
        raise ValidationError("No file was provided. Upload the NASA GISTEMP CSV first.")

    try:
        if isinstance(source, str):
            with open(source, "r", encoding="utf-8-sig") as fh:
                text = fh.read()
        elif isinstance(source, (bytes, bytearray)):
            text = bytes(source).decode("utf-8-sig")
        else:  # file-like object (e.g. Streamlit UploadedFile)
            raw = source.read()
            text = raw.decode("utf-8-sig") if isinstance(raw, (bytes, bytearray)) else raw
    except FileNotFoundError:
        raise ValidationError(f"File not found: {source}") from None
    except UnicodeDecodeError:
        raise ValidationError("The file is not readable text. Please upload the CSV file from NASA.") from None

    lines = text.splitlines()
    header_idx = next((i for i, ln in enumerate(lines)
                       if ln.strip().lower().startswith("year,")), None)
    if header_idx is None:
        raise ValidationError(
            "Could not find the header row starting with 'Year,'. "
            "This does not look like a NASA GISTEMP CSV (expected GLB.Ts+dSST.csv).")

    df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])),
                     na_values=["***", "****", "*****", ""])
    df.columns = [str(c).strip() for c in df.columns]
    return clean_giss_dataframe(df)


def clean_giss_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate structure, coerce numbers, and drop repeated header rows."""
    if "Year" not in df.columns:
        raise ValidationError("The data has no 'Year' column.")
    if not any(c in df.columns for c in ANNUAL_COLUMNS):
        raise ValidationError("The data has no annual column ('J-D' or 'D-N').")

    df = df.copy()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["Year"])  # drops stray header/text rows
    if df.empty:
        raise ValidationError("The file contains no valid year rows.")
    df["Year"] = df["Year"].astype(int)
    for col in df.columns:
        if col != "Year":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.drop_duplicates(subset="Year").sort_values("Year").reset_index(drop=True)
    return df


def get_series(df: pd.DataFrame, column: str = "J-D") -> pd.DataFrame:
    """Return a two-column DataFrame [Year, Anomaly] with missing values removed."""
    if column not in df.columns:
        raise ValidationError(f"Column '{column}' is not in the data.")
    out = df[["Year", column]].rename(columns={column: "Anomaly"}).dropna()
    out = out.reset_index(drop=True)
    if len(out) < 2:
        raise ValidationError(
            f"Column '{column}' has fewer than 2 valid values; cannot analyse it.")
    return out


def missing_report(df: pd.DataFrame, column: str = "J-D") -> pd.DataFrame:
    """Years in the file's range where `column` has no value."""
    return df.loc[df[column].isna(), ["Year", column]].reset_index(drop=True)


# ----------------------------------------------------------------------------
# 2. Input validation
# ----------------------------------------------------------------------------
def parse_year(value, name: str = "Year") -> float:
    """Convert user input to a finite number, or raise ValidationError."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{name} is required.")
    try:
        year = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be a number (got {value!r}).") from None
    if not np.isfinite(year):
        raise ValidationError(f"{name} must be a finite number.")
    return year


def validate_interpolation_year(series: pd.DataFrame, year) -> float:
    """Year must lie inside [first, last] observed year."""
    y = parse_year(year)
    lo, hi = float(series["Year"].min()), float(series["Year"].max())
    if y < lo or y > hi:
        raise ValidationError(
            f"{y:g} is outside the observed range {lo:g}-{hi:g}. "
            "Interpolation only works inside the range; use the Extrapolation page instead.")
    return y


def validate_extrapolation_year(series: pd.DataFrame, year, max_horizon: int = 100) -> float:
    """Year must be after the last observed year (and within a sensible horizon)."""
    y = parse_year(year)
    hi = float(series["Year"].max())
    if y <= hi:
        raise ValidationError(
            f"{y:g} is not beyond the last observed year ({hi:g}). "
            "Use the Interpolation page for years inside the data range.")
    if y > hi + max_horizon:
        raise ValidationError(
            f"{y:g} is more than {max_horizon} years past the data. Please choose a nearer year.")
    return y


# ----------------------------------------------------------------------------
# 3. Interpolation
# ----------------------------------------------------------------------------
def linear_interpolate(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    """y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)"""
    if x1 == x0:
        raise ValidationError("Cannot interpolate: the two known years are identical.")
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


@dataclass
class InterpolationResult:
    year: float
    value: float
    x0: float
    y0: float
    x1: float
    y1: float
    is_observed: bool  # True if the year already has an observed value


def interpolate_at(series: pd.DataFrame, year) -> InterpolationResult:
    """Linear interpolation using the nearest valid observations on each side."""
    y = validate_interpolation_year(series, year)
    years = series["Year"].to_numpy(dtype=float)
    vals = series["Anomaly"].to_numpy(dtype=float)

    exact = np.where(years == y)[0]
    if exact.size:
        v = float(vals[exact[0]])
        return InterpolationResult(y, v, y, v, y, v, True)

    right = int(np.searchsorted(years, y))  # first index with year > y
    left = right - 1
    x0, y0, x1, y1 = years[left], vals[left], years[right], vals[right]
    return InterpolationResult(y, linear_interpolate(y, x0, y0, x1, y1),
                               x0, y0, x1, y1, False)


def interpolate_many(series: pd.DataFrame, years) -> pd.DataFrame:
    """Vectorised helper: values on a list of years inside the range."""
    out = [(r.year, r.value, r.is_observed) for r in (interpolate_at(series, y) for y in years)]
    return pd.DataFrame(out, columns=["Year", "Value", "IsObserved"])


def fill_missing_years(df: pd.DataFrame, column: str = "J-D") -> pd.DataFrame:
    """Interpolated estimates for years inside the file whose value is missing."""
    s = get_series(df, column)
    rows = []
    for yr in missing_report(df, column)["Year"]:
        if s["Year"].min() < yr < s["Year"].max():
            rows.append((int(yr), interpolate_at(s, yr).value))
    return pd.DataFrame(rows, columns=["Year", "Anomaly"])


# ----------------------------------------------------------------------------
# 4. Trend fitting and extrapolation
# ----------------------------------------------------------------------------
@dataclass
class TrendFit:
    slope: float       # deg C per year
    intercept: float
    r_squared: float
    start_year: int
    end_year: int
    n_points: int

    def predict(self, years):
        return self.intercept + self.slope * np.asarray(years, dtype=float)


def fit_linear_trend(series: pd.DataFrame, start_year: Optional[int] = None,
                     end_year: Optional[int] = None) -> TrendFit:
    """Least-squares straight line y = a + b*year over [start_year, end_year]."""
    s = series
    if start_year is not None:
        s = s[s["Year"] >= start_year]
    if end_year is not None:
        s = s[s["Year"] <= end_year]
    if len(s) < 2:
        raise ValidationError("Need at least 2 observations in the chosen period to fit a trend.")
    x = s["Year"].to_numpy(dtype=float)
    y = s["Anomaly"].to_numpy(dtype=float)
    if np.ptp(x) == 0:
        raise ValidationError("All selected observations are from the same year.")
    slope, intercept = np.polyfit(x, y, 1)
    ss_res = float(np.sum((y - (intercept + slope * x)) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return TrendFit(float(slope), float(intercept), float(r2),
                    int(x.min()), int(x.max()), int(len(s)))


@dataclass
class ExtrapolationResult:
    year: float
    value: float
    method: str
    slope: float
    intercept: float
    based_on: str
    horizon_years: float


METHOD_TWO_POINT = "Two-point line (last two observations)"
METHOD_TREND = "Least-squares trend (last N years)"
METHODS = [METHOD_TWO_POINT, METHOD_TREND]


def extrapolate_at(series: pd.DataFrame, year, method: str = METHOD_TREND,
                   window: int = 30, max_horizon: int = 100) -> ExtrapolationResult:
    """Estimate a value beyond the last observed year with a straight line."""
    y = validate_extrapolation_year(series, year, max_horizon)
    last_year = float(series["Year"].max())

    if method == METHOD_TWO_POINT:
        a, b = series.iloc[-2], series.iloc[-1]
        slope = (b["Anomaly"] - a["Anomaly"]) / (b["Year"] - a["Year"])
        intercept = b["Anomaly"] - slope * b["Year"]
        based_on = f"{int(a['Year'])} and {int(b['Year'])}"
    elif method == METHOD_TREND:
        if int(window) < 2:
            raise ValidationError("The window must be at least 2 years.")
        fit = fit_linear_trend(series, start_year=int(last_year) - int(window) + 1)
        slope, intercept = fit.slope, fit.intercept
        based_on = f"{fit.start_year}-{fit.end_year} ({fit.n_points} values)"
    else:
        raise ValidationError(f"Unknown method: {method}")

    return ExtrapolationResult(y, float(intercept + slope * y), method,
                               float(slope), float(intercept), based_on, y - last_year)


# ----------------------------------------------------------------------------
# 5. Trend summary
# ----------------------------------------------------------------------------
def trend_summary(series: pd.DataFrame) -> dict:
    full = fit_linear_trend(series)
    warm = series.loc[series["Anomaly"].idxmax()]
    cold = series.loc[series["Anomaly"].idxmin()]
    out = {
        "first_year": int(series["Year"].iloc[0]),
        "last_year": int(series["Year"].iloc[-1]),
        "n_values": int(len(series)),
        "warmest_year": int(warm["Year"]), "warmest_value": float(warm["Anomaly"]),
        "coldest_year": int(cold["Year"]), "coldest_value": float(cold["Anomaly"]),
        "full_slope_per_decade": full.slope * 10,
        "full_r2": full.r_squared,
        "change_first_to_last": float(series["Anomaly"].iloc[-1] - series["Anomaly"].iloc[0]),
    }
    if len(series[series["Year"] >= out["last_year"] - 29]) >= 2:
        recent = fit_linear_trend(series, start_year=out["last_year"] - 29)
        out["recent_slope_per_decade"] = recent.slope * 10
        out["recent_r2"] = recent.r_squared
        out["recent_start"] = recent.start_year
    return out


def decade_averages(series: pd.DataFrame) -> pd.DataFrame:
    s = series.copy()
    s["Decade"] = (s["Year"] // 10) * 10
    g = s.groupby("Decade")["Anomaly"].agg(["mean", "count"]).reset_index()
    g.columns = ["Decade", "Mean anomaly (deg C)", "Years with data"]
    return g


# ----------------------------------------------------------------------------
# 6. Combined results table (for graph + CSV download)
# ----------------------------------------------------------------------------
TYPE_OBSERVED = "Observed (NASA)"
TYPE_INTERP = "Interpolated estimate"
TYPE_EXTRAP = "Extrapolated estimate"


def build_results_table(series: pd.DataFrame, interpolations=None,
                        extrapolations=None) -> pd.DataFrame:
    """Stack observed + estimates into one labelled table."""
    obs = series.assign(Type=TYPE_OBSERVED, Method="NASA GISTEMP v4")
    parts = [obs]
    if interpolations:
        parts.append(pd.DataFrame(
            [{"Year": r.year, "Anomaly": r.value, "Type": TYPE_INTERP,
              "Method": f"Linear between {r.x0:g} and {r.x1:g}"}
             for r in interpolations if not r.is_observed]))
    if extrapolations:
        parts.append(pd.DataFrame(
            [{"Year": r.year, "Anomaly": r.value, "Type": TYPE_EXTRAP,
              "Method": f"{r.method}; based on {r.based_on}"}
             for r in extrapolations]))
    out = pd.concat([p for p in parts if len(p)], ignore_index=True)
    out = out.rename(columns={"Anomaly": "Anomaly_degC_vs_1951-1980"})
    return out.sort_values("Year").reset_index(drop=True)


# ----------------------------------------------------------------------------
# 7. Back-test: how good is extrapolation on years we already know?
# ----------------------------------------------------------------------------
def backtest_extrapolation(series: pd.DataFrame, holdout: int = 10,
                           method: str = METHOD_TREND, window: int = 30) -> pd.DataFrame:
    """Hide the last `holdout` observed years, extrapolate them from earlier
    data only, then compare with what was really observed."""
    holdout = int(holdout)
    if holdout < 1:
        raise ValidationError("Hold-out must be at least 1 year.")
    train = series.iloc[:-holdout].reset_index(drop=True)
    test = series.iloc[-holdout:]
    if len(train) < 3:
        raise ValidationError("Not enough data left for training; reduce the hold-out.")
    last_train = float(train["Year"].max())
    rows = []
    for _, r in test.iterrows():
        if r["Year"] <= last_train:
            continue
        est = extrapolate_at(train, r["Year"], method, window)
        rows.append((int(r["Year"]), float(r["Anomaly"]), est.value,
                     est.value - float(r["Anomaly"])))
    out = pd.DataFrame(rows, columns=["Year", "Observed", "Extrapolated", "Error"])
    if out.empty:
        raise ValidationError("No years available for back-testing.")
    return out
