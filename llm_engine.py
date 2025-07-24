import os
import re
import ast
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-70b-8192")


def _extract_code_blocks(response_text: str) -> str:
    fence = r"```(?:python)?\n([\s\S]*?)```"
    matches = re.findall(fence, response_text, flags=re.IGNORECASE)
    return "\n".join(matches) if matches else response_text


def _clean_intro(code_text: str) -> str:
    phrases = [
        "Here is the code", "Below is the code", "Sure! Here's",
        "The following code", "You can use this code", "# Example"
    ]
    lower = code_text.lower()
    for p in phrases:
        idx = lower.find(p.lower())
        if idx != -1:
            return code_text[idx + len(p):].strip()
    return code_text


def _validate_python(code: str) -> str:
    valid_lines = []
    for line in code.splitlines():
        try:
            ast.parse(line)
            valid_lines.append(line)
        except SyntaxError:
            continue
    return "\n".join(valid_lines)


def generate_analysis_code(signal_name: str, analysis_goal: str) -> str:
    """
    Generate a self-contained Python snippet that:
      - Accepts: df (DataFrame), output_dir (str), data_paths (for comparative)
      - Plots either a single-series or comparative histogram per analysis_goal
      - Uses Freedman–Diaconis binning, seaborn styling, tick locators
      - **Auto‐generates** a descriptive subtitle based on the goal
      - Saves the figure to output_dir
    """
    system_prompt = f"""
You are a Python Data Engineer and Data Visualization Expert.
Write only runnable Python code (no placeholders) that:

1. Imports:
   import pandas as pd
   import numpy as np
   import seaborn as sns
   import matplotlib.pyplot as plt
   from matplotlib.ticker import AutoLocator, AutoMinorLocator
   from mdf_extractor import read_mdf_signal

2. Detects whether the goal is **comparative** (if 'comparative' in the goal text):
is_comp = 'comparative' in analysis_goal.lower()
   if is_comp is True, build a comparative histogram:
     • Read each file in `data_paths` (CSV via `pd.read_csv`, else `read_mdf_signal`)
     • Extract `{signal_name}`, assign a `Vehicle` label per filename
     • Compute `duration = time.diff().fillna(0)`
     • Concatenate into `long_df`
     • Plot with sns.histplot(..., hue='Vehicle', weights='duration'):
     fig, ax = plt.subplots(figsize=(12,7))
     sns.histplot(
       data=long_df,
       x="{signal_name}",
       hue="Vehicle",
       weights="duration",
       element="bars",
       multiple="layer",
       palette="colorblind",
       edgecolor="black",
       alpha=1.0,
       ax=ax
     )
    Otherwise (single-series):
     • Drop NaNs, cast to float
     • Compute Freedman–Diaconis bins (cap between 10 and 60)
     • Plot with `sns.histplot(data=data, bins=bins, element='bars', multiple='layer', ...)`

3. Styling for both:
   sns.set_style('whitegrid')
   sns.set_context('paper', font_scale=1.1)
   plt.rcParams['font.family'] = 'DejaVu Sans'
   ax.xaxis.set_major_locator(AutoLocator()); ax.xaxis.set_minor_locator(AutoMinorLocator(4))
   ax.yaxis.set_major_locator(AutoLocator()); ax.yaxis.set_minor_locator(AutoMinorLocator(4))
   ax.grid(which='major', linestyle='--', alpha=0.7)
   ax.grid(which='minor', linestyle=':', alpha=0.4)

4. Axis labels:
    X: signal name + unit (detect from name, e.g. "V" for "volt", "km/h" for "speed")
    Y: "Total Duration [s]" if is_comp else "Frequency"

5. title = ("Comparative Histogram of " if is_comp else "Histogram of ") + "{signal_name}"
ax.set_title(title, fontsize=(18 if is_comp else 16), fontweight="bold")

6. Subtitle: auto‑generate a concise description (e.g.
“Distribution of battery voltage levels” or
“Total duration per voltage bin across vehicles”)
and add via:
ax.text(
  0.5, -0.12,
  subtitle,                
  transform=ax.transAxes,
  ha="center",
  fontsize=12,
  fontweight="bold",
  color="gray"
)
7. Finish with:
    plt.tight_layout()
    plt.savefig(output_dir + '/<descriptive>.png')
User request: **{analysis_goal}** on signal **{signal_name}**.
"""

    user_message = "Please generate the complete Python code block to achieve this."

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ],
        "temperature": 0.0,
        "max_tokens": 1200
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(GROQ_API_URL, json=payload, headers=headers)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]

    code = _extract_code_blocks(raw)
    code = _clean_intro(code)
    return _validate_python(code).strip()
