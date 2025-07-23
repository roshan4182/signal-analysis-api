import os
import tempfile
from typing import List, Tuple
from fastapi import UploadFile

def save_uploads(files: List[UploadFile]) -> Tuple[str, List[str]]:
    """
    Saves uploaded files to a temporary directory.
    Returns (temp_dir, list_of_file_paths).
    """
    tmp = tempfile.mkdtemp(prefix="analysis_")
    paths: List[str] = []
    for f in files:
        out = os.path.join(tmp, f.filename)
        with open(out, "wb") as dest:
            dest.write(f.file.read())
        paths.append(out)
    return tmp, paths
