import json
from decimal import Decimal
from datetime import date, datetime
import pandas as pd

def make_json_safe(value):
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if pd.isna(value):
        return None

    return value


def dataframe_to_llm_json(df: pd.DataFrame, max_rows: int = 100) -> str:
    if df is None or df.empty:
        return "[]"

    df_to_send = df.copy()

    records = df_to_send.to_dict(orient="records")

    safe_records = [
        {key: make_json_safe(value) for key, value in row.items()}
        for row in records
    ]

    payload = {
        "row_count": len(df),
        "rows_sent_to_llm": len(safe_records),
        "columns": list(df.columns),
        "data": safe_records
    }

    return json.dumps(payload, ensure_ascii=False, indent=2)



def tool_result_to_df(tool_result_json: str):
    try:
        payload = json.loads(tool_result_json)
        result = payload.get("result", [])
        return pd.DataFrame(result)
    except Exception:
        return pd.DataFrame()