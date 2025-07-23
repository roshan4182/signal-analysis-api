import os
import io
import json
import zipfile
import shutil
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import StreamingResponse

from file_handler import save_uploads
from executor import execute_analysis

app = FastAPI()

@app.post("/analyze")
async def analyze(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    signal_names: str = Form(...),
    analysis_goals: str = Form(...),
    use_fallback: str = Form("false"),
):
    # 1) Saves uploads to a temp dir
    temp_dir, data_paths = save_uploads(files)

    # 2) Parse's signals & goals
    signals = [s.strip() for s in signal_names.split(",") if s.strip()]
    goals_dict = json.loads(analysis_goals)
    goals = [goals_dict.get(sig, "") for sig in signals]

    # 3) Convert's fallback flag to boolean
    fb = use_fallback.lower() in ("true", "1", "yes", "on")
    print("⚙️ use_fallback parsed as:", fb)

    # 4) Runs the analysis
    results = execute_analysis(
        data_paths=data_paths,
        signals=signals,
        goals=goals,
        output_dir=temp_dir,
        use_fallback=fb,
    )
    print("⚙️ execute_analysis results:", results)

    # 5) Bundling results into a ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, path in results.items():
            if os.path.isfile(path):
                zf.write(path, arcname=os.path.basename(path))
            else:
                # write error text directly
                zf.writestr(name, path)
    buf.seek(0)

    # 6) Scheduling cleanup of temp_dir after response
    background.add_task(shutil.rmtree, temp_dir, True)

    # 7) Returning the ZIP file
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="analysis_output.zip"'},
    )
