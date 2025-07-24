import pandas as pd

def normalize_time(df: pd.DataFrame, time_col: str = 'time') -> pd.DataFrame:
    df = df.copy()
    # if there's no time column, leave the frame unchanged
    if time_col not in df.columns:
        return df
    #otherwise zero base it
    
    df[time_col] = df[time_col] - df[time_col].iloc[0]
    return df
