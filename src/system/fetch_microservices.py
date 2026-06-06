from src.connectors.db_connector import get_data

def fetch_all_microservices():
    sql = """
        select description, name
        from microservices
            where
            active = TRUE            
        order by created_at desc       
    """
    try:
        rows = get_data(sql,)
    except Exception as e:
        return False
    return rows[0] if rows else False
