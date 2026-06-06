from src.system.load_microservice import load_microservice_sql
from src.connectors.db_connector import get_data
import pandas as pd
from src.microservices.helpers import dataframe_to_llm_json


def microManager(route, logger=None):
    logger = logger or (lambda *_: None)
    userId = f"server_{route}"

    if not route:
        return None, "Microservice route is missing.", userId

    try:
        logger(f"Loading SQL for microservice: {route}")
        sql = load_microservice_sql(route)

        if not sql:
            return None, f"Microservice {route} not found or inactive.", userId

        logger(f"Executing SQL for microservice: {route}")
        sql_data = get_data(sql)

        if not sql_data:
            return None, f"Microservice {route} returned no data.", userId

        user_microservice_object = pd.DataFrame(sql_data)

        if user_microservice_object.empty:
            return None, f"Microservice {route} returned empty result.", userId

        logger(f"Microservice {route} returned {len(user_microservice_object)} rows")

        user_backend_message = user_microservice_object
        llm_backend_message = dataframe_to_llm_json(user_microservice_object)

        return user_backend_message, llm_backend_message, userId

    except Exception as e:
        logger(f"Microservice  {route} failed: {e}")
        return None, f"Microservice {route} failed: {str(e)}", userId


