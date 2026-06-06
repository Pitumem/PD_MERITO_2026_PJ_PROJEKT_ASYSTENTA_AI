import json
import pandas as pd


def run_analytics_tool(data: pd.DataFrame, tool_decision: dict, user_question: str = "") -> str:
    """
    Dispatcher for analytical tools.
    Input:
        data: full report DataFrame
        tool_decision: JSON parsed from tool_selector LLM
        user_question: original user question
    Output:
        JSON string passed to analyst prompt
    """

    if data is None or data.empty:
        return json.dumps({
            "tool_executed": False,
            "reason": "Report data is empty."
        }, ensure_ascii=False)

    if not tool_decision.get("use_tool"):
        return None

    tool_name = tool_decision.get("tool_name")

    if tool_name in ["top_1", "top_n", "bottom_1", "bottom_n"]:
        return top_n_tool(
            data=data,
            tool_decision=tool_decision,
            user_question=user_question,
            tool_name=tool_name
        )

    return json.dumps({
        "tool_executed": False,
        "reason": f"Unsupported tool: {tool_name}",
        "tool_name": tool_name
    }, ensure_ascii=False, indent=2)

def build_standouts(result_df: pd.DataFrame, available_metrics: list) -> dict:
    standouts = {}

    if result_df is None or result_df.empty:
        return standouts

    if "margin_value" in available_metrics and "margin_value" in result_df.columns:
        standouts["highest_margin_value"] = (
            result_df.sort_values("margin_value", ascending=False)
            .head(1)
            .to_dict(orient="records")[0]
        )

    if "total_margin_percent" in available_metrics and "total_margin_percent" in result_df.columns:
        standouts["highest_margin_percent"] = (
            result_df.sort_values("total_margin_percent", ascending=False)
            .head(1)
            .to_dict(orient="records")[0]
        )

        standouts["lowest_margin_percent_in_result"] = (
            result_df.sort_values("total_margin_percent", ascending=True)
            .head(1)
            .to_dict(orient="records")[0]
        )

    if "total_customer" in available_metrics and "total_customer" in result_df.columns:
        standouts["highest_customer_count"] = (
            result_df.sort_values("total_customer", ascending=False)
            .head(1)
            .to_dict(orient="records")[0]
        )

    if "total_eaches" in available_metrics and "total_eaches" in result_df.columns:
        standouts["highest_quantity"] = (
            result_df.sort_values("total_eaches", ascending=False)
            .head(1)
            .to_dict(orient="records")[0]
        )

    return standouts

def top_n_tool(data: pd.DataFrame, tool_decision: dict, user_question: str = "", tool_name: str = "") -> str:
    df = data.copy()

    metric_column = tool_decision.get("metric_column")
    filters = tool_decision.get("filters", [])
    group_by = tool_decision.get("group_by", [])
    if tool_name == "top_1":
        limit = 1
        sort_direction = "desc"

    elif tool_name == "top_n":
        limit = int(tool_decision.get("limit") or 10)
        sort_direction = "desc"

    elif tool_name == "bottom_1":
        limit = 1
        sort_direction = "asc"

    elif tool_name == "bottom_n":
        limit = int(tool_decision.get("limit") or 10)
        sort_direction = "asc"

    if not metric_column:
        return _fail("Missing metric_column.", data)

    if metric_column not in df.columns:
        return _fail(f"Metric column not found: {metric_column}", data)

    for column in group_by:
        if column not in df.columns:
            return _fail(f"Group by column not found: {column}", data)

    rows_before_filter = len(df)

    # Apply filters
    for f in filters:
        column = f.get("column")
        operator = f.get("operator", "=")
        value = f.get("value")

        if column not in df.columns:
            return _fail(f"Filter column not found: {column}", data)

        if operator == "=":
            df = df[df[column].astype(str) == str(value)]
        elif operator == "contains":
            df = df[df[column].astype(str).str.contains(str(value), case=False, na=False)]
        else:
            return _fail(f"Unsupported filter operator: {operator}", data)

    rows_after_filter = len(df)

    if df.empty:
        return json.dumps({
            "tool_executed": False,
            "reason": "No rows after applying filters.",
            "filters": filters,
            "rows_before_filter": rows_before_filter,
            "rows_after_filter": rows_after_filter
        }, ensure_ascii=False, indent=2)

    BUSINESS_METRICS = [
        "total_turnover",
        "margin_value",
        "total_margin_percent",
        "total_customer",
        "total_eaches"
    ]

    available_metrics = [
        col for col in BUSINESS_METRICS
        if col in df.columns
    ]

    if metric_column not in available_metrics:
        available_metrics.append(metric_column)

    # Convert all available metrics to numeric
    for col in available_metrics:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=[metric_column])

    if df.empty:
        return json.dumps({
            "tool_executed": False,
            "reason": f"No numeric values available for metric_column: {metric_column}",
            "metric_column": metric_column
        }, ensure_ascii=False, indent=2)

    # Aggregate all useful business metrics, not only selected metric
    if group_by:
        agg_dict = {}

        for col in available_metrics:
            if col == "total_margin_percent":
                agg_dict[col] = "mean"
            else:
                agg_dict[col] = "sum"

        grouped = (
            df.groupby(group_by, as_index=False, dropna=False)
            .agg(agg_dict)
        )
    else:
        grouped = df.copy()

    ascending = sort_direction == "asc"

    ranked = grouped.sort_values(
        by=metric_column,
        ascending=ascending
    ).reset_index(drop=True)

    result_df = ranked.head(limit)

    total_metric = float(grouped[metric_column].sum())
    group_count = len(grouped)

    result_records = result_df.to_dict(orient="records")

    main_result = result_records[0] if result_records else None
    main_value = float(main_result[metric_column]) if main_result else None

    second_place = ranked.iloc[1].to_dict() if len(ranked) > 1 else None
    second_value = float(second_place[metric_column]) if second_place else None

    difference_to_second_place = None
    comparison_to_second_place = ""

    if main_value is not None and second_value is not None:
        if sort_direction == "asc":
            difference_to_second_place = second_value - main_value
            comparison_to_second_place = "main_result_is_lower_than_second_place"
        else:
            difference_to_second_place = main_value - second_value
            comparison_to_second_place = "main_result_is_higher_than_second_place"

    share_of_total = None
    if total_metric and main_value is not None:
        share_of_total = main_value / total_metric

    top_5_context = ranked.head(5).to_dict(orient="records")

    top_n_total = float(result_df[metric_column].sum())
    top_n_share_of_total = top_n_total / total_metric if total_metric else None

    standouts = build_standouts(result_df, available_metrics)

    payload = {
        "tool_executed": True,
        "tool_name": tool_decision.get("tool_name"),
        "user_question": user_question,
        "scope": {
            "metric_column": metric_column,
            "filters": filters,
            "group_by": group_by,
            "limit": limit,
            "sort_direction": sort_direction
        },
        "result": result_records,
        "context": {
            "rows_before_filter": rows_before_filter,
            "rows_after_filter": rows_after_filter,
            "group_count": group_count,
            "available_business_metrics": available_metrics,
            "total_metric": total_metric,
            "main_result_share_of_total": share_of_total,
            "second_place": second_place,
            "difference_to_second_place": difference_to_second_place,
            "comparison_to_second_place": comparison_to_second_place,
            "top_5_context": top_5_context,
            "top_n_total": top_n_total,
            "top_n_share_of_total": top_n_share_of_total,
            "standouts_inside_result": standouts
        },
        "note": "The result was calculated deterministically in Python. If sort_direction is asc, the first result is the lowest value. If sort_direction is desc, the first result is the highest value. The analyst must not reverse this interpretation."
    }

    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)

def _fail(reason: str, data: pd.DataFrame) -> str:
    return json.dumps({
        "tool_executed": False,
        "reason": reason,
        "available_columns": list(data.columns) if data is not None else []
    }, ensure_ascii=False, indent=2)