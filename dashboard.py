import os
import io
import json
import zipfile
import tempfile
import requests
import streamlit as st
API_URL = st.secrets.get(
    "API_URL",
    os.getenv("API_URL", "http://127.0.0.1:8000/analyze")
)


st.set_page_config(page_title="📊 Smart Measurement Analyzer", layout="wide")
st.title("🚗📉 Generative AI Measurement Analysis Tool")

st.markdown(
    """
    Upload one or more measurement files (.mf4, .csv, etc.), enter your signals,
    and define specific analysis goals for each. Our AI will do the rest.
    """
)

# --- File upload & inputs ---
uploaded_files = st.file_uploader(
    "📁 Upload your measurement files",
    type=None,
    accept_multiple_files=True
)

signals_input = st.text_input(
    "🧪 Enter signal names (comma-separated)",
    value="signal_name1, signal_name2"
)
signal_list = [s.strip() for s in signals_input.split(",") if s.strip()]

# Per-signal goals
goals: dict[str, str] = {}
for sig in signal_list:
    goals[sig] = st.text_area(
        f"📝 Analysis goal for '{sig}'", placeholder="e.g., Histogram of battery voltage"
    )

use_fallback = st.checkbox(
    "Use fallback plots if AI-generated code fails",
    value=True
)
# --- Trigger analysis ---
if st.button("🚀 Run Analysis"):
    if not uploaded_files or not signal_list or not any(goals.values()):
        st.warning("Please upload files, list signals, and set at least one goal.")
    else:
        with st.spinner("Analyzing..."):
            try:
                # Preparing multipart form
                files_payload = [
                    ("files", (file.name, file.read(), file.type))
                    for file in uploaded_files
                ]
                form_data = [
                    ("signal_names", ",".join(signal_list)),
                    ("analysis_goals", json.dumps(goals)),
                    ("use_fallback", str(use_fallback).lower()),
                ]

                resp = requests.post(
                    API_URL,
                    files=files_payload,
                    data=form_data,
                    timeout=60
                )
                resp.raise_for_status()

                # Reads ZIP from response
                zip_bytes = io.BytesIO(resp.content)
                zip_data = zip_bytes.getvalue()
                # Use a unique temp directory for extraction
                out_dir = tempfile.mkdtemp(prefix="temp_output_")
                with zipfile.ZipFile(zip_bytes, "r") as zf:
                    zf.extractall(out_dir)
                    image_files = [f for f in zf.namelist() if f.lower().endswith(".png")]

                st.success("✅ Analysis complete!")
                cols = st.columns(3)
                for idx, img in enumerate(image_files):
                    img_path = os.path.join(out_dir, img)
                    with cols[idx % 3]:
                        st.image(
                            img_path,
                            caption=os.path.basename(img),
                            use_container_width=True
                        )

                st.download_button(
                    label="⬇️ Download Full Report (.zip)",
                    data=zip_data,
                    file_name="analysis_output.zip",
                    mime="application/zip"
                )

            except requests.exceptions.Timeout:
                st.error("⏰ Request timed out (60s). Is the API up and reachable?")
            except requests.exceptions.ConnectionError as e:
                st.error(f"❌ Connection error: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
