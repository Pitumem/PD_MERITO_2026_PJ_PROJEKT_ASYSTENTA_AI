import psycopg
from psycopg.rows import dict_row
import streamlit as st

DB_URL = st.secrets["DATABASE_URL"]

def get_data(sql, params=None):
    if params is None:
        params = ()

    with psycopg.connect(DB_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            conn.commit()
            return rows
        
        
def post_data(sql, params=None):
    if params is None:
        params = ()

    with psycopg.connect(DB_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()