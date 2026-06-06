from src.connectors.db_connector import get_data, post_data
from datetime import datetime, timezone


def update_token_balance(user_id, tokens_used):
    select_sql = """
        SELECT current_token, token_limit
        FROM users
        WHERE id = %s
    """
    rows = get_data(select_sql, (user_id,))
    if not rows:
        return {"success": False, "error": "User not found"}
    else:
        if rows[0]["current_token"] is None:
            token_base = rows[0]["token_limit"]
        else:
            token_base = rows[0]["current_token"]

    timestamp = datetime.now(timezone.utc)
    new_balance = token_base - tokens_used
    active = new_balance > 0

    update_sql = """
        UPDATE users
        SET current_token = %s,
            is_active = %s,
            last_used = %s
        WHERE id = %s
    """

    post_data(update_sql, (new_balance, active, timestamp, user_id))

    return {
        "success": True,
        "token_balance": new_balance,
        "tokens_used": tokens_used,
        "active": active,
        "last_used": timestamp
    }