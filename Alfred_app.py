import mysql.connector
from sqlalchemy import create_engine
import sqlalchemy
import streamlit as st

import pandas as pd


##-------------------------------------------------SETTINGS-----------------------------------------------------------##
##----------LAYOUT SETUP----------
st.set_page_config(layout='wide', page_title = 'Alfred 4', page_icon = '📈')
hide_menu_style = """
       <style>
       #MainMenu {visibility: hidden; }
       footer {visibility: hidden;}
       </style>
       """
st.markdown(hide_menu_style, unsafe_allow_html=True)

risk = st.secrets['risk'] #<--------using static risk

##----------DATABASE SETUP--------
host = st.secrets['db_host']
user = st.secrets['db_user']
password = st.secrets['db_password']

@st.cache(hash_funcs={sqlalchemy.engine.base.Engine: id})
def db_connect(db):
    return create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{db}")

@st.cache(allow_output_mutation=True, hash_funcs={sqlalchemy.engine.base.Engine: id})
def run_query(connection, query, index_col = None):
    return pd.read_sql_query(query, connection, index_col)

positions = db_connect('positions')
prices = db_connect('prices')

updated = run_query(prices, "SELECT Updated FROM symbol_list LIMIT 1")

option = st.radio('', options = ['Positions','Position Calc','Orders','Sectors','Scanner','Watchlist'])
st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html = True)

st.caption(f'Updated: {updated.iat[0,0]}')
st.markdown(f"<h1 style='text-align: center; color: black;'>{option}</h1>", unsafe_allow_html=True)\


open_positions = run_query(positions, "SELECT * FROM open_positions", 'symbol')
open_orders = run_query(positions, "SELECT * FROM open_orders", 'symbol')
closed_orders = run_query(positions, "SELECT * FROM closed_orders", 'symbol')
closed_positions = closed_orders.copy()

st.table(open_positions)
st.table(open_orders)
st.table(closed_positions)
st.table(closed_orders)
