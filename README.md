# signal-analysis-api

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://signal-analysis-api.streamlit.app)

&#x20; &#x20;

An API and dashboard for generating styled histograms and summary reports from MDF or CSV measurement data, powered by an LLM engine with robust fallbacks.

## Table of Contents

* [Features](#features)
* [Quickstart](#quickstart)
* [Installation](#installation)
* [Usage](#usage)

  * [API](#running-the-api)
  * [Dashboard](#using-the-streamlit-dashboard)
* [Examples](#examples)
* [Postman Collection](#postman-collection)
* [Testing](#testing)
* [Docker](#docker-optional)
* [Contributing](#contributing)
* [License](#license)
* [Authors](#authors)

---

## Features

* **MDF & CSV ingestion** via `pandas` and `asammdf`
* **LLM-driven plotting**: dynamic Python code for single-series & comparative histograms with Freedman–Diaconis binning
* **Fallback routines** in `plot_utils.py` for reliability
* **Summary statistics**: mean, std, min/max, skewness, kurtosis
* **Streamlit dashboard** for interactive exploration
* **Docker-ready** for easy deployment

---

## Quickstart

Run analysis with a single command (assuming Docker installed):

```bash
# Build and run
docker build -t signal-analysis-api:latest .
docker run --rm -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  signal-analysis-api:latest \
  uvicorn main:app --host 0.0.0.0 --port 8000

# Analyze data
curl -X POST http://localhost:8000/analyze \
  -F "files=@/path/to/data.mf4" \
  -F "signal_names=speed" \
  -F 'analysis_goals={"speed":"distribution of vehicle speed"}' \
  --output output.zip
```

---

## Installation

1. **Clone** the repo:

   ```bash
   git clone git@github.com:roshan4182/signal-analysis-api.git
   cd signal-analysis-api
   ```
2. **Create & activate** a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install** dependencies:

   ```bash
   pip install -r requirements.txt
   ```
4. **Configure** environment (create `.env`):

   ```ini
   GROQ_API_KEY=your_groq_api_key
   GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions
   GROQ_MODEL=llama3-70b-8192
   ```

---

## Live Demo

Try the deployed services:

## Live Demo

Try the deployed services:

- **API (docs):** https://signal-analysis-api-2nwy.onrender.com/docs  
- **Dashboard:**  https://signal-analysis-api.streamlit.app


---

## Usage

### Running the API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Endpoint: `/analyze` (POST)

* **Description**: Analyze files; returns a ZIP of charts and reports.
* **Fields**:

  * `files`: MDF4 or CSV (multiple).
  * `signal_names`: Comma-separated list of signals.
  * `analysis_goals`: JSON map of signal to goal.
  * `use_fallback`: `true`/`false` to force fallback.

See [Examples](#examples) for detailed commands.

### Using the Streamlit Dashboard

```bash
pip install streamlit
streamlit run dashboard.py
```

Open [http://localhost:8501](http://localhost:8501), upload files, enter signals/goals, and analyze.

---

## Examples

### Single-series Histogram

```bash
curl -X POST http://localhost:8000/analyze \
  -F "files=@vehicle.csv" \
  -F "signal_names=speed" \
  -F 'analysis_goals={"speed":"distribution of speed"}' \
  --output speed_analysis.zip
```

**Output ZIP** contains:

* `histogram_speed.png`
* `speed_summary.txt`

### Comparative Histogram

```bash
curl -X POST http://localhost:8000/analyze \
  -F "files=@run1.mf4" \
  -F "files=@run2.mf4" \
  -F "signal_names=battery_voltage" \
  -F 'analysis_goals={"battery_voltage":"comparative histogram of battery voltage across runs"}' \
  --output battery_voltage.zip
```

**Output ZIP** contains:

* `comparative_battery_voltage.png`
* `battery_voltage_summary.txt`

---

## Postman Collection

Import the [Postman collection](./postman_collection.json) for interactive testing.


---

## Testing

```bash
pytest tests/
```

---

## Docker (Optional)

```bash
docker build -t signal-analysis-api:latest .

docker run -p 8000:8000 --env-file .env signal-analysis-api:latest
```

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the Code of Conduct.

---

## Authors

* **Your Name** – Initial design & implementation
* **Collaborators** – Feedback & testing

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
