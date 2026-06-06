from src.connectors.db_connector import get_data

def load_prompt(prompt_type="general"):
    sql = """
        select prompt
        from prompts
            where
            active = TRUE
            and type = %s
        order by created_at desc
        limit 1
    """
    try:
        rows = get_data(sql, (prompt_type,))
    except Exception as e:
        return False
    return rows[0]["prompt"] if rows else False