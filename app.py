import mysql.connector
from sqlalchemy import create_engine
import sqlalchemy

import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import numpy as np


##-------------------------------------------------SETTINGS-----------------------------------------------------------##
##----------LAYOUT SETUP----------
st.set_page_config(layout='wide', page_title = 'Alfred 4', page_icon = '📈')
#st.markdown("<style>#MainMenu {visibility: hidden; } footer {visibility: hidden;}</style>", unsafe_allow_html=True)

risk = st.secrets['risk'] #<--------using static risk

##----------DATABASE SETUP--------
host = st.secrets['db_host']
user = st.secrets['db_user']
password = st.secrets['db_password']

@st.cache(hash_funcs={sqlalchemy.engine.base.Engine: id})
def db_connect(db):
    return create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{db}")

# @st.cache(allow_output_mutation=True, hash_funcs={sqlalchemy.engine.base.Engine: id}, ttl = 10)
def run_query(connection, query, index_col = None):
    return pd.read_sql_query(query, connection, index_col)

positions = db_connect('positions')
prices = db_connect('prices')

open_positions = run_query(positions, "SELECT * FROM open_positions", 'symbol')
open_orders = run_query(positions, "SELECT * FROM open_orders", 'symbol')
closed_orders = run_query(positions, "SELECT * FROM closed_orders", 'symbol')
closed_positions = closed_orders.copy()



##---------------------------------------------DASHBOARD ELEMENTS-----------------------------------------------------##
##----------HEADER----------------
updated = run_query(positions, "SELECT Updated FROM updated")
option = st.radio('', options = ['Positions','Position Calc','Orders','Sectors','Scanner','Watchlist'])

st.markdown("<style>div.row-widget.stRadio > div{flex-direction:row;}</style>", unsafe_allow_html = True)
st.caption(f'Updated: {updated.iat[0,0]}')
st.markdown(f"<h1 style='text-align: center; color: black;'>{option}</h1>", unsafe_allow_html=True)

##----------POSITIONS SCREEN------
if option == 'Positions':
    # Calcs
    unrealized_pnl = '{0:.2f}'.format(open_positions['unrlzd p&l'].sum() / risk) + ' R'
    realized_pnl = '{0:.2f}'.format(closed_orders['rlzd p&l'].sum() / risk) + ' R'
    total_pnl = '{0:.2f}'.format((open_positions['unrlzd p&l'].sum() + closed_orders['rlzd p&l'].sum()) / risk, 2) + ' R'
    total_open_risk = '{0:.2f}'.format(open_positions['open risk'].sum() / risk) + ' R'

    # Format open positions table
    open_positions['rlzd p&l'] /= risk
    open_positions['unrlzd p&l'] /= risk
    open_positions['open risk'] /= risk
    
    # Format closed positions table
    ls = []
    for i in range(0, len(closed_positions), 1):
        if closed_positions.iloc[i]['action'] == 'BUY' and closed_positions.iloc[i]['rlzd p&l'] != 0:
            ls.append('short')
        elif closed_positions.iloc[i]['action'] == 'SELL' and closed_positions.iloc[i]['rlzd p&l'] != 0:
            ls.append('long')
        else:
            ls.append(np.nan)
    closed_positions['l/s'] = ls
    closed_positions = closed_positions[closed_positions['status'] == 'Filled']  # filter for filled trades only
    closed_positions = closed_positions[(closed_positions['l/s'] == 'long') | (closed_positions['l/s'] == 'short')]
    closed_positions = closed_positions.drop(columns = ['action', 'type', 'status', 'time', 'price', 'filled qty', 'comm.'])
    closed_positions['entry'], closed_positions['stop'], closed_positions['target'], closed_positions['unrlzd p&l'] = 0, 0, 0, 0  # not avaialbe yet
    closed_positions.rename(columns = {'filled at': 'exit'}, inplace = True)
    closed_positions = closed_positions[['l/s', 'qty', 'entry', 'exit', 'stop', 'target', 'unrlzd p&l', 'rlzd p&l']]
    closed_positions['rlzd p&l'] /= risk
    closed_positions['unrlzd p&l'] /= risk
    
    # Positions summary
    '---' 
    one, two, three, four = st.columns([4, 9, 3, 4]) 
    with two:
        st.header(f'Current P&L: {total_pnl}')
        st.text(f'Unrealized: {unrealized_pnl}')
        st.text(f'Realized: {realized_pnl}')
    with three:
        st.header('Risk:')
        st.text(f'Total open risk: {total_open_risk}')
    
    # Positions table
    '---' 
    one, two, three = st.columns([1, 3, 1])
    with two:
        open_positions.sort_values(by= 'unrlzd p&l', inplace = True, ascending = False)
        st.text(f'{len(open_positions)} trade in progress...' if len(open_positions) == 1 else
                f'{len(open_positions)} trades in progress...')
        st.table(open_positions.style.format({'qty': '{0:.2f}',
                                                     'entry': '{0:.2f}',
                                                     'last': '{0:.2f}',
                                                     'stop': '{0:.2f}',
                                                     'target': '{0:.2f}',
                                                     'unrlzd p&l': '{0:.2f} R',
                                                     'rlzd p&l': '{0:.2f} R',
                                                     'open risk': '{0:.2f} R'},
                                                      na_rep = 'N/A'))
        if len(closed_positions) > 0:
            closed_positions.sort_values(by = 'rlzd p&l', inplace = True, ascending = False)
            st.text(f'{len(closed_positions)} closed trade' if len(closed_positions) == 1 else
                    f'{len(closed_positions)} closed trades')
            st.table(closed_positions.style.format({'qty': '{0:.2f}',
                                                           'entry': '{0:.2f}',
                                                           'exit': '{0:.2f}',
                                                           'stop': '{0:.2f}',
                                                           'target': '{0:.2f}',
                                                           'unrlzd p&l': '{0:.2f} R',
                                                           'rlzd p&l': '{0:.2f} R'},
                                                            na_rep = 'N/A'))
    # TradingView Chart
    one, two, three = st.columns([1, 3, 1])
    with two:
        selections = list(open_positions.index.values) + list(closed_positions.index.values) + ['SPY']
        tradingview = open('tradingview.html', 'r', encoding = 'utf-8')
        source_code = tradingview.read()

        select = st.selectbox('', (selections))
        source_code = source_code.replace('AAPL', select)
        components.html(source_code, height = 800)
        
##----------ORDERS SCREEN---------
if option == 'Orders':
    # Open orders
    '---'
    st.text(f'{len(open_orders)} open orders')
    st.dataframe(open_orders.style.format({'qty': '{0:.2f}',
                                              'price': '{0:.2f}'},
                                              na_rep = 'N/A'))
    # Closed orders
    st.text(f'{len(closed_orders)} closed orders')
    closed_orders.sort_values(by= 'status', inplace = True, ascending = False)
    closed_orders.drop(columns = ['rlzd p&l']
    st.dataframe(closed_orders.style.format({'qty': '{0:.2f}',
                                                'price': '{0:.2f}',
                                                'filled at':  '{0:.2f}',
                                                'filled qty': '{0:.2f}',
                                                'comm.': '{0:.2f}',
                                                'rlzd p&l': '{0:.2f}'},
                                                na_rep = 'N/A'))
