# ClimateTrend

Interactive Streamlit app demonstrating **interpolation** and **extrapolation** on the
official NASA GISS global temperature dataset (GISTEMP v4).
Mini-project, Topic 8: *Interpolation, Extrapolation, and Climate Change*.

## Problem statement
Develop an interactive Python application that uses historical global temperature anomaly data
to demonstrate interpolation and extrapolation in the context of climate change. Users can
visualise historical trends, estimate values between observed data points (interpolation), and
explore mathematical estimates beyond the observed range (extrapolation), with the limitations
of these estimates clearly explained.

## About the dataset (documented structure)
* Source: <https://data.giss.nasa.gov/gistemp/data_v4.html>
* File: `GLB.Ts+dSST.csv` (global-mean monthly, seasonal and annual means)
  - direct link: <https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv>
* Values are temperature **anomalies** in **degrees Celsius**, relative to the **1951-1980** average.
* Line 1 is a title, line 2 is the header `Year,Jan,...,Dec,J-D,D-N,DJF,MAM,JJA,SON`.
* `J-D` = Jan-Dec annual mean, `D-N` = Dec-Nov annual mean. Missing values appear as `***`.
* **No climate data is bundled with this project.** You supply the file (upload in the app).

## Project structure
```
ClimateTrend/
  app.py                  Streamlit interface (pages, plots, downloads)
  climate_analysis.py     Maths + data loading/validation (no Streamlit code)
  requirements.txt
  README.md
  data/README.txt         Optional place to put GLB.Ts+dSST.csv
  tests/test_climate_analysis.py   Automated tests (unittest; pytest also works)
  .streamlit/config.toml  Theme colours
```

## Windows installation and execution (Command Prompt)

Requires Python 3.9+ from <https://www.python.org/downloads/> (tick "Add python.exe to PATH" when installing).
If `python` is not recognised below, use `py` instead of `python`.

1. **Download and extract the ZIP** (Windows 10/11):
   ```
   cd %USERPROFILE%\Downloads
   tar -xf ClimateTrend.zip
   ```
   (Or right-click the ZIP -> Extract All.)
2. **Open Command Prompt in the project folder:**
   ```
   cd %USERPROFILE%\Downloads\ClimateTrend
   ```
3. **Create a virtual environment:**
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
   The prompt should now start with `(venv)`.
4. **Install dependencies:**
   ```
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. **Run the app:**
   ```
   streamlit run app.py
   ```
6. **Open in a browser:** it usually opens automatically; otherwise go to <http://localhost:8501>.
7. **Upload the NASA dataset:** download `GLB.Ts+dSST.csv` from the link above, open the **Data**
   page in the sidebar, and use *Upload GLB.Ts+dSST.csv*. (Alternatively save the file as
   `data\GLB.Ts+dSST.csv` and tick *Load ... from the project folder*.)
8. **Run the tests** (open a second Command Prompt, or press Ctrl+C to stop the app first):
   ```
   cd %USERPROFILE%\Downloads\ClimateTrend
   venv\Scripts\activate
   python -m unittest discover -s tests -v
   ```
   or, equivalently: `pytest -v`

## How the app works
| Page | What it does |
|---|---|
| Home | Title, problem statement, objectives, dataset facts |
| Data | Upload/load CSV, validation messages, summary, trend graph, filterable table |
| Interpolation | Linear interpolation formula, step-by-step substitution, result and graph; fills missing years |
| Extrapolation | Two-point or least-squares straight-line estimate beyond the last year, strong warnings, and a **back-test** on years already observed |
| Trend analysis | Warmest/coldest years, linear slope per decade for a chosen period, decade averages |
| Comparison & download | One graph with observed, interpolated and extrapolated values (distinct colours/markers); CSV downloads |
| Limitations | Plain-language explanation of what these estimates can and cannot tell you |

Colour code everywhere: **blue = observed (NASA)**, **green = interpolated**, **red = extrapolated**.

Formulas:
* Interpolation: `y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)`
* Least-squares line: `b = sum((xi - mean_x)(yi - mean_y)) / sum((xi - mean_x)^2)`, `a = mean_y - b*mean_x`

Input validation covers: no file / unreadable file / wrong file layout, missing annual column,
non-numeric or blank years, years outside the valid range for each tool, too few valid values,
and missing (`***`) values (skipped in calculations; interpolation can estimate them).

## Important limitation
Extrapolating a straight line is **not a climate forecast**. Real projections use physics-based
climate models and emissions scenarios.

## Tests
`tests/test_climate_analysis.py` covers loading, interpolation, extrapolation, back-testing,
trend summary and input validation. Its tiny CSV is a clearly labelled **test fixture**
(round made-up numbers in the NASA file layout so answers can be checked by hand) and is not NASA data.
