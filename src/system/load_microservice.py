from src.connectors.db_connector import get_data

def load_microservice_sql(microservice_route):
    sql = """
        select sql
        from microservices
            where
            active = TRUE
            and name = %s
        order by created_at desc
        limit 1
    """
    try:
        rows = get_data(sql, (microservice_route,))
    except Exception as e:
        return False
    return rows[0]["sql"] if rows else False

def fetch_all_microservices():
    sql = """
        select description, name
        from microservices
            where
            active = TRUE            
        order by created_at desc       
    """
    try:
        rows = get_data(sql)
    except Exception:
        return []

    return rows if rows else []
