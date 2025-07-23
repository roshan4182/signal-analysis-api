import os
from plot_utils import compute_summary_statistics

def write_report(df, signal: str, output_dir: str) -> str:
    """
    Writes a text file of summary statistics for `signal` in `df`.
    Returns the path to the .txt file.
    """
    stats = compute_summary_statistics(df, signal)
    lines = [f"{k}: {v:.3f}" for k, v in stats.items()]
    report_path = os.path.join(output_dir, f"{signal}_analysis.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    return report_path
