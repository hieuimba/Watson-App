import mysql.connector
from sqlalchemy import create_engine
import sqlalchemy

import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import numpy as np
import matplotlib

from ta import volatility

##-------------------------------------------------SETTINGS-----------------------------------------------------------##
##----------LAYOUT SETUP----------
st.set_page_config(layout = 'wide', page_title = 'Alfred 4', page_icon = '🎩')
# st.markdown("<style>#MainMenu {visibility: hidden; } footer {visibility: hidden;}</style>", unsafe_allow_html=True)

risk = st.secrets['risk']  # <--------using static risk

##----------DATABASE SETUP--------
host = st.secrets['db_host']
user = st.secrets['db_user']
password = st.secrets['db_password']


@st.cache(hash_funcs = {sqlalchemy.engine.base.Engine: id})
def db_connect(db):
    return create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{db}")


@st.cache(allow_output_mutation = True, hash_funcs = {sqlalchemy.engine.base.Engine: id}, ttl = 3600)
def run_query_cached(connection, query, index_col = None):
    return pd.read_sql_query(query, connection, index_col)
    connection.close()


def run_query(connection, query, index_col = None):
    return pd.read_sql_query(query, connection, index_col)
    connection.close()


positions = db_connect('positions')
prices = db_connect('prices')

##---------------------------------------------DASHBOARD ELEMENTS-----------------------------------------------------##
##----------HEADER----------------
updated = run_query(positions, "SELECT Updated FROM updated")
