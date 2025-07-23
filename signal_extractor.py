import pandas as pd

def normalize_time(df: pd.DataFrame, time_col: str = 'time') -> pd.DataFrame:
    """
    Subtracts the first timestamp so that time starts at zero.
    """
    df = df.copy()
    df[time_col] = df[time_col] - df[time_col].iloc[0]
    return df
