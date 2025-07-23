import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import skew, kurtosis
from matplotlib.ticker import AutoLocator, AutoMinorLocator
from asammdf import MDF
from mdf_extractor import read_mdf_signal
from signal_extractor import normalize_time

#  1) Summary stats for reporter.py 

def compute_summary_statistics(df: pd.DataFrame, signal_name: str) -> dict:
    s = df[signal_name].dropna().astype(float)
    return {
        "mean": s.mean(),
        "std": s.std(),
        "min": s.min(),
        "max": s.max(),
        "skewness": skew(s),
        "kurtosis": kurtosis(s),
    }

#  2) Metadata for friendly labels/units 

_SIGNAL_META = {
    "Eng_nEng10ms":    ("Engine Speed", "rpm"),
    "Eng_uBatt":       ("Battery Voltage", "mV"),
    "FuSHp_pRailBnk1": ("Fuel Pressure", "MPa"),
}

def _get_label_and_unit(signal: str) -> tuple[str, str]:
    return _SIGNAL_META.get(signal, (signal, ""))

#  3) Common styling helper 

def _apply_common_style(
    ax: plt.Axes,
    display_name: str,
    unit: str,
    chart_type: str,
    subtitle: str | None = None
) -> None:
    ax.set_title(display_name, fontsize=16, fontweight="bold")
    txt = subtitle or f"{chart_type} of {display_name}"
    ax.text(
        0.5, -0.12, txt,
        transform=ax.transAxes,
        ha="center",
        fontsize=12,
        fontweight="bold",
        color="gray"
    )
    # Axis labels
    xlabel = f"{display_name} [{unit}]" if unit else display_name
    ax.set_xlabel(xlabel, fontsize=12, fontstyle="italic")
    if chart_type.lower() != "pie chart":
        ax.set_ylabel("Frequency", fontsize=12, fontstyle="italic")
        ax.xaxis.set_major_locator(AutoLocator())
        ax.xaxis.set_minor_locator(AutoMinorLocator(4))
        ax.tick_params(which="minor", length=3)
        ax.grid(True, linestyle="--", alpha=0.7)
    sns.despine(trim=True)

#  4) Single-series histogram 

def plot_histogram(df: pd.DataFrame, signal_name: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    sns.set_style("whitegrid")
    sns.set_context("paper", font_scale=1.1)
    plt.rcParams["font.family"] = "DejaVu Sans"

    data = df[signal_name].dropna().astype(float).to_numpy()
    if data.size > 1:
        q75, q25 = np.percentile(data, [75, 25])
        iqr = q75 - q25
        bw = 2 * iqr / (len(data) ** (1/3)) if iqr > 0 else None
        n_bins = int(np.ceil((data.max() - data.min()) / bw)) if bw else 50
    else:
        n_bins = 50
    bins = max(10, min(n_bins, 60))

    fig, ax = plt.subplots(figsize=(10, 6))
    color = sns.color_palette("colorblind", 1)[0]
    sns.histplot(
        data=data,
        bins=bins,
        element="bars",
        multiple="layer",
        color=color,
        edgecolor=color,
        alpha=0.6,
        ax=ax
    )

    display_name, unit = _get_label_and_unit(signal_name)
    _apply_common_style(ax, display_name, unit, chart_type="Histogram")

    out = os.path.join(output_dir, f"histogram_{signal_name}.png")
    plt.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out

#  5) Pie chart fallback 

def plot_pie(df: pd.DataFrame, signal_name: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    sns.set_style("whitegrid")
    plt.rcParams["font.family"] = "DejaVu Sans"

    counts = df[signal_name].value_counts()
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(counts, labels=counts.index, autopct="%1.1f%%")
    display_name, unit = _get_label_and_unit(signal_name)
    _apply_common_style(
        ax, display_name, unit,
        chart_type="Pie chart",
        subtitle=f"Distribution of {display_name}"
    )
    out = os.path.join(output_dir, f"pie_{signal_name}.png")
    plt.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out

#  6) Time series fallback 

def plot_time_series(df: pd.DataFrame, signal_name: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    sns.set_style("whitegrid")
    plt.rcParams["font.family"] = "DejaVu Sans"

    fig, ax = plt.subplots(figsize=(12, 6))
    x = df.get("timestamp", df.get("time", df.index))
    ax.plot(x, df[signal_name], linewidth=1.5)

    display_name, unit = _get_label_and_unit(signal_name)
    _apply_common_style(ax, display_name, unit, chart_type="Time Series")

    out = os.path.join(output_dir, f"time_series_{signal_name}.png")
    plt.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out

# 7) Summary stats box 

def plot_summary_box(stats: dict, signal_name: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    sns.set_style("whitegrid")
    plt.rcParams["font.family"] = "DejaVu Sans"

    fig, ax = plt.subplots(figsize=(6, 4))
    names, vals = list(stats.keys()), list(stats.values())
    sns.barplot(x=names, y=vals, palette="pastel", ax=ax)
    display_name, unit = _get_label_and_unit(signal_name)
    _apply_common_style(
        ax, display_name, unit,
        chart_type="Summary Stats",
        subtitle="Key summary statistics"
    )
    out = os.path.join(output_dir, f"summary_stats_{signal_name}.png")
    plt.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out

#  8) Comparative histogram 
def plot_comparative_histogram(
    data_paths: list[str],
    signal_name: str,
    output_dir: str
) -> str:
    import os
    from matplotlib.patches import Patch

    os.makedirs(output_dir, exist_ok=True)
    sns.set_style("whitegrid")
    sns.set_context("paper", font_scale=1.1)
    plt.rcParams["font.family"] = "DejaVu Sans"

    # Friendly label & unit
    display_name, unit = _get_label_and_unit(signal_name)
    # Determine display unit and scale
    if unit.lower() == "mv":
        unit_disp = "V"
        scale = 1e-3
    else:
        unit_disp = unit
        scale = 1.0

    # Load & weight each series
    series_list, durations_list, labels = [], [], []
    for path in data_paths:
        lbl = os.path.basename(path).rsplit(".", 1)[0]
        df0 = pd.read_csv(path) if path.lower().endswith(".csv") else read_mdf_signal(path, signal_name)
        df0 = normalize_time(df0, time_col="time")
        raw = df0[signal_name].astype(float).to_numpy()
        v = raw * scale
        t = df0["time"].astype(float).to_numpy()
        dt = np.diff(t, prepend=t[0])
        series_list.append(v)
        durations_list.append(dt)
        labels.append(lbl)

    # Shared Freedman–Diaconis bins
    all_vals = np.concatenate(series_list)
    if all_vals.size > 1:
        q75, q25 = np.percentile(all_vals, [75, 25])
        iqr = q75 - q25
        bw = 2 * iqr / (len(all_vals) ** (1/3)) if iqr > 0 else None
        nbins = int(np.ceil((all_vals.max() - all_vals.min()) / bw)) if bw else 50
    else:
        nbins = 50
    bins = max(10, min(nbins, 60))

    # Plot layers
    fig, ax = plt.subplots(figsize=(12, 7))
    palette = sns.color_palette("colorblind", len(series_list))
    handles, legend_labels = [], []

    for i, (v, dt, lbl) in enumerate(zip(series_list, durations_list, labels), start=1):
        ax.hist(
            v,
            bins=bins,
            weights=dt,
            histtype="stepfilled",
            alpha=0.6,
            color=palette[i - 1],
            edgecolor=palette[i - 1],
            linewidth=1.2
        )
        mn, mx = v.min(), v.max()
        handles.append(Patch(facecolor=palette[i - 1], edgecolor=palette[i - 1]))
        legend_labels.append(f"{i}. {lbl} [{mn:.2f};{mx:.2f}]")

    # Axis labels & grid
    ax.set_xlabel(f"{display_name} [{unit_disp}]", fontsize=14, fontstyle="italic")
    ax.set_ylabel("Duration [s]", fontsize=14, fontstyle="italic")
    ax.xaxis.set_major_locator(AutoLocator())
    ax.xaxis.set_minor_locator(AutoMinorLocator(4))
    ax.tick_params(which="minor", length=3)
    ax.grid(axis="x", linestyle="--", alpha=0.7)
    ax.grid(axis="y", visible=False)
    sns.despine(trim=True)

    # Title in top-left margin
    fig.text(
        0.02, 0.98,
        display_name,
        fontsize=18,
        fontweight="bold",
        va="top",
        ha="left"
    )

    # Legend just outside the top-right of the axes
    ax.legend(
        handles=handles,
        labels=legend_labels,
        title="Vehicle",
        fontsize=10,
        title_fontsize=11,
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        ncol=1
    )
    # Shrink axes to leave margin for legend
    fig.subplots_adjust(right=0.75)

    # Subtitle under x-axis
    ax.text(
        0.5, -0.12,
        f"Comparative Histogram of {display_name}",
        transform=ax.transAxes,
        ha="center",
        fontsize=12,
        fontweight="bold",
        color="gray"
    )
    # Save
    out = os.path.join(output_dir, f"comparative_{signal_name}.png")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out
