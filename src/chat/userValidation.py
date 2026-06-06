
from src.connectors.db_connector import get_data

def validateUser(user_id):
    sql = """
        select current_token
            from users
            where id = %s
              and is_active = true
              and (expires_at is null or expires_at > now())
        
    """
    try:
        rows = get_data(sql, (user_id,))
    except Exception as e:
        return {"allowed" : False,
                "tokens" : 0}
    return{"allowed" : True if rows and rows[0]["current_token"] > 0 else False,
            "tokens" : rows[0]["current_token"] if rows else 0}
