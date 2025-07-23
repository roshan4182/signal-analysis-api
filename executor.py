import os
import re
import traceback
from typing import List, Dict
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from llm_engine import generate_analysis_code
from mdf_extractor import read_mdf_signal
from signal_extractor import normalize_time
from reporter import write_report

def sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[\s\n]+", "_", s)
    s = re.sub(r"[^0-9A-Za-z_-]", "", s)
    return s or "analysis"

def read_signal_dataframe(data_paths: List[str], signal: str) -> pd.DataFrame:
    dfs = []
    for path in data_paths:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(path)
        else:
            df = read_mdf_signal(path, signal)
        df = normalize_time(df, time_col="time")
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True).sort_values("time").reset_index(drop=True)

def execute_analysis(
    data_paths: List[str],
    signals: List[str],
    goals: List[str],
    output_dir: str,
    use_fallback: bool = False
) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    results: Dict[str, str] = {}

    # static unit mapping
    unit_map = {
        "mv": "V",
        "volt": "V",
        "batt": "V",
        "speed": "km/h",
        "pressure": "bar",
    }
    for signal, goal in zip(signals, goals):
        clean_goal = sanitize_filename(goal)
        signal_dir = os.path.join(output_dir, f"{signal}_{clean_goal}")
        os.makedirs(signal_dir, exist_ok=True)

        df      = read_signal_dataframe(data_paths, signal)
        is_comp = "comparative" in goal.lower()
        fname   = f"{'comparative_' if is_comp else 'histogram_'}{signal}.png"

        try:
            # 1) get LLM snippet
            raw = generate_analysis_code(signal, goal)

            # 2) strip comments and stray calls
             # only drop empty lines and comments; keep ax.text(...) intact
            lines = [
                ln for ln in raw.splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            core = "\n".join(lines)

            # 3) fallback inject if needed
            if "sns.histplot" not in core:
                if is_comp:
                    core = """
long_df = pd.concat([
    (pd.read_csv(p) if p.lower().endswith('.csv') else read_mdf_signal(p, signal))
      .assign(
          time=lambda d: d['time'].astype(float),
          duration=lambda d: d['time'].diff().fillna(0),
          Vehicle=os.path.basename(p).rsplit('.',1)[0]
      )
    for p in data_paths
], ignore_index=True)

vals = long_df[signal].to_numpy()
q75, q25 = np.percentile(vals, [75,25])
iqr = q75 - q25
bw = 2 * iqr / (len(vals)**(1/3)) if iqr>0 else None
nbins = int(np.ceil((vals.max()-vals.min())/bw)) if bw else 50
bins = max(10, min(nbins,60))

sns.histplot(
    data=long_df,
    x=signal,
    hue="Vehicle",
    weights="duration",
    element="bars",
    multiple="layer",
    palette="colorblind",
    edgecolor="black",
    alpha=1.0,
    bins=bins,
    ax=ax
)
"""
                else:
                    core = """
data = df[signal].dropna().astype(float).to_numpy()
q75, q25 = np.percentile(data, [75,25])
iqr = q75 - q25
bw = 2 * iqr / (len(data)**(1/3)) if iqr>0 else None
nbins = int(np.ceil((data.max()-data.min())/bw)) if bw else 50
bins = max(10, min(nbins,60))

sns.histplot(
    data=data,
    bins=bins,
    element="bars",
    multiple="layer",
    color=sns.color_palette("colorblind")[0],
    edgecolor="black",
    alpha=1.0,
    ax=ax
)
"""

                # 4) wrap and execute core plotting snippet
            wrapper = f"""
import os
from matplotlib.ticker import AutoMinorLocator, MaxNLocator
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize={(12,7) if is_comp else (10,6)})
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.1)
plt.rcParams["font.family"] = "DejaVu Sans"

# Major ticks with a cap on count and pruning
ax.xaxis.set_major_locator(MaxNLocator(nbins=8, prune='both'))
ax.yaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))

# Keep fine-grained minors
ax.xaxis.set_minor_locator(AutoMinorLocator(4))
ax.yaxis.set_minor_locator(AutoMinorLocator(4))

ax.grid(which="major", linestyle="--", alpha=0.7)
ax.grid(which="minor", linestyle=":", alpha=0.4)
{core}
"""
            # execute the wrapper and grab back ax
            ns = {
                "df": df.copy(),
                "data_paths": data_paths,
                "read_mdf_signal": read_mdf_signal,
                "pd": pd, "np": np, "sns": sns, "plt": plt,
                "os": os, "signal": signal
            }
            exec(wrapper, ns)
            ax = ns["ax"]

            # 5) Set axis labels and title (don't override LLM subtitle)
            unit_map = {"mv":"V","volt":"V","batt":"V","speed":"km/h","pressure":"bar"}
            unit = next((u for k,u in unit_map.items() if k in signal.lower()), "")
            ax.set_xlabel(f"{signal} [{unit}]" if unit else signal, fontsize=14, fontstyle="italic")
            ax.set_ylabel("Total Duration [s]" if is_comp else "Frequency", fontsize=14, fontstyle="italic")
            ax.set_title(f"{'Comparative Histogram of ' if is_comp else 'Histogram of '}{signal}",
                         fontsize=(18 if is_comp else 16), fontweight="bold")

            plt.tight_layout()
            out_path = os.path.join(signal_dir, fname)
            plt.savefig(out_path)
            results[fname] = out_path

            # 6) report
            rpt = write_report(df, signal, signal_dir)
            results[os.path.basename(rpt)] = rpt

        except Exception as ex:
            traceback.print_exc()
            if use_fallback:
                from plot_utils import plot_histogram, plot_comparative_histogram
                try:
                    if is_comp:
                        png = plot_comparative_histogram(data_paths, signal, signal_dir)
                    else:
                        png = plot_histogram(df, signal, signal_dir)
                    results[os.path.basename(png)] = png
                    rpt = write_report(df, signal, signal_dir)
                    results[os.path.basename(rpt)] = rpt
                except Exception as fe:
                    results[f"{signal}_fallback_error.txt"] = str(fe)
            else:
                results[f"{signal}_error.txt"] = str(ex)

    return results
