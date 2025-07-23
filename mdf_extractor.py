import pandas as pd
from asammdf import MDF

def read_mdf_signal(path: str, signal: str) -> pd.DataFrame:
    """
    Reads a single signal from an MDF4 file into a DataFrame with columns:
    - 'time' (float seconds)
    - <signal> (float samples)
    """
    mdf = MDF(path)
    sig = mdf.get(signal)
    return pd.DataFrame({
        'time': sig.timestamps.astype(float),
        signal: sig.samples.astype(float)
    })
