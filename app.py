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
st.set_page_config(layout='wide', page_title = 'Alfred 4', page_icon = '📈')
st.markdown("<style>#MainMenu {visibility: hidden; } footer {visibility: hidden;}</style>", unsafe_allow_html=True)

risk = st.secrets['risk'] #<--------using static risk

##----------DATABASE SETUP--------
host = st.secrets['db_host']
user = st.secrets['db_user']
password = st.secrets['db_password']

@st.cache(hash_funcs={sqlalchemy.engine.base.Engine: id})
def db_connect(db):
    return create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{db}")

@st.cache(allow_output_mutation=True, hash_funcs={sqlalchemy.engine.base.Engine: id})
def run_query_cached(connection, query, index_col = None):
    return pd.read_sql_query(query, connection, index_col)

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
    closed_orders.drop(columns = ['rlzd p&l'], inplace = True)
    st.dataframe(closed_orders.style.format({'qty': '{0:.2f}',
                                                'price': '{0:.2f}',
                                                'filled at':  '{0:.2f}',
                                                'filled qty': '{0:.2f}',
                                                'comm.': '{0:.2f}'},
                                                na_rep = 'N/A'))

    
##----------SECTORS SCREEN--------
sector_list = ['SPY', 'XLE', 'XLI', 'XLK', 'XLY', 'XLF', 'XLB', 'XLP', 'XLV', 'XLU', 'XLRE', 'XLC', 'IWM', 'QQQ']
if option == 'Sectors':
    # Select period
    '---'
    beta_list = []
    matrix = pd.DataFrame()
    std_dev = pd.DataFrame()

    one, two = st.columns([1,5])
    with one:
        options = st.radio('Select period:', options = ['1 M', '3 M', '6 M', '1 Y', '2 Y'], help ='1 month = 21 trading days')
        if options == '1 M':
            period = 21
        elif options == '3 M':
            period = 63
        elif options == '6 M':
            period = 126
        elif options == '1 Y':
            period = 252
        elif options == '2 Y':
            period = 504
            
    # Translation table
    with two:
        sector_name = ['S&P 500 ETF', 'Energy', 'Industrials', 'Technology', 'Consumer Discretionary',
                       'Financials', 'Materials', 'Consumer Staples', 'Health Care', 'Utilities',
                       'Real Estate', 'Communication Services', 'Russell 2000 ETF', 'Invesco QQQ Trust']
        sector_trans = pd.DataFrame(data = sector_name, columns = ['Name'], index = sector_list)
        st.table(sector_trans.T)
    
    # Correlation table
    spy = run_query_cached(prices, "SELECT * FROM etf_price WHERE symbol = 'SPY'")
    spy['return%'] = spy['Close'].pct_change(1) * 100
    spy = spy.tail(period)
    spy['var'] = spy['return%'].var()
    for i in range(0, len(sector_list)):
        sector = run_query_cached(prices, f"SELECT * FROM etf_price WHERE symbol = '{sector_list[i]}'")
        sector['return%'] = sector['Close'].pct_change(1) * 100
        sector = sector.tail(period)
        matrix[f'{sector_list[i]}'] = sector['return%'].values
        corr_matrix = matrix.corr()

        sector['bm_return%'] = spy['return%'].to_list()
        cov_df = sector[['return%', "bm_return%"]].cov()
        bm_var = spy.iloc[-1]['var']
        beta = cov_df.iloc[1, 0] / bm_var
        beta_list.append(beta)

    temp = pd.DataFrame(index = sector_list)
    temp['Beta'] = beta_list
    temp = temp.T
    corr_matrix = corr_matrix.append(temp)
    u = corr_matrix.index.get_level_values(0)
    corr_matrix = corr_matrix.style.background_gradient(cmap = 'Oranges', axis = None, low = -0.5, subset = pd.IndexSlice[u[:-1], :])
    corr_matrix = corr_matrix.background_gradient(cmap = 'Greens', axis = None, subset = pd.IndexSlice[u[-1], :])
    st.table(corr_matrix.format(precision = 3))

    
##----------CALC SCREEN-----------
if option == 'Position Calc':
    '---'
    symbol_list = run_query_cached(prices, "SELECT symbol FROM symbol_list")
    symbol_list = symbol_list['symbol'].to_list()
    
    beta_list = []
    matrix = pd.DataFrame()
    std_dev = pd.DataFrame()

    one, two, three = st.columns([2,3,1])
    with one:
        risk_options = [10, 20, 30, 50, 80, 100]
        risk = st.selectbox(label = '$ Risk', options = risk_options, index = 1)
        entry = st.number_input(label='Entry', value = 2.00, step = 0.1)
        stop = st.number_input(label='Stop', value = 1.00, step = 0.1)
        target = entry + (entry - stop)
        distance = round(entry - stop, 2)
        distance_percent = round(abs(distance) / entry, 2) * 100
        size = round(risk / abs(distance), 3)
        dollar_size = round(size * entry, 2)
        direction = 'Long' if distance > 0 else 'Short'
        st.number_input('Target', min_value = target, max_value = target, value =target)
        st.text(f'Direction: {direction}')
        st.subheader(f'Size: {size} share' if size == 1 else f'Size: {size} shares')
        ''
        st.text(f'$ Equivalent: $ {dollar_size}')
        st.subheader('R table:')
        price_range = [stop, stop + distance/2, entry, entry+ distance/2, target, entry + distance*2]
        price_range = pd.DataFrame(price_range, columns = ['Price'],
                                                index = ['-1 R', '-1.5 R', '0 R', '0.5 R', '1 R', '2 R']).T
        st.table(price_range.style.format(precision = 2))
    with three:
        options = st.radio('Select period:', options = ['1 M', '3 M', '6 M', '1 Y'], help ='1 month = 21 trading days')
        if options == '1 M':
            period = 21
        elif options == '3 M':
            period = 63
        elif options == '6 M':
            period = 126
        elif options == '1 Y':
            period = 252
    with two:
        symbol = st.multiselect('Select symbols:', options = symbol_list, default = ['SPY'] + open_positions.index.values.tolist())

        spy = run_query_cached(prices, "SELECT * FROM etf_price WHERE symbol = 'SPY'")
        spy['return%'] = spy['Close'].pct_change(1) * 100
        spy = spy.tail(period)
        spy['var'] = spy['return%'].var()

        for i in range(0, len(symbol)):
            if symbol[i] in sector_list:
                bars = run_query_cached(prices, f"SELECT * FROM etf_price WHERE symbol = '{symbol[i]}'")
                bars = bars.fillna('N/A')
            else:
                bars = run_query_cached(prices, f"SELECT * FROM stock_price WHERE symbol = '{symbol[i]}'")
                bars = bars.fillna('N/A')
            bars['atr'] = volatility.AverageTrueRange(bars['High'], bars['Low'], bars['Close'],
                                                      window = 21).average_true_range()
            bars['return%'] = bars['Close'].pct_change(1) * 100
            if i == len(symbol) -1:
                bars['std dev'] = bars['return%'].rolling(21).std()
                bars['ATR'] = volatility.AverageTrueRange(bars['High'], bars['Low'], bars['Close'],
                                                          window = 21).average_true_range()
                bars['avg vol'] = bars['Volume'].rolling(21).mean()
            bars = bars.tail(period)
            matrix[f'{symbol[i]}'] = bars['return%'].values
            corr_matrix = matrix.corr()

            bars['bm_return%'] = spy['return%'].to_list()
            cov_df = bars[['return%', "bm_return%"]].cov()
            bm_var = spy.iloc[-1]['var']
            beta = cov_df.iloc[1, 0] / bm_var
            beta_list.append(beta)

        temp = pd.DataFrame(index = symbol)
        temp['Beta-M'] = beta_list
        temp = temp.T
        temp2 = pd.DataFrame(index = symbol)
        temp2['Beta-S'] = 0
        temp2 = temp2.T
        corr_matrix = corr_matrix.append(temp)
        corr_matrix = corr_matrix.append(temp2)
        u = corr_matrix.index.get_level_values(0)
        corr_matrix = corr_matrix.style.background_gradient(cmap = 'RdYlGn_r', axis = None,
                                                            subset = pd.IndexSlice[u[:-2], :])
        # corr_matrix = corr_matrix.background_gradient(cmap = 'White', axis = None, subset = pd.IndexSlice[u[-1], :])
        st.table(corr_matrix.format(precision = 3))


        st.text(f"Symbol: {bars.iloc[-1]['Symbol']},    Name: {bars.iloc[-1]['Name']},    Sector: {bars.iloc[-1]['Sector']}")
        st.text(f"Last: {bars.iloc[-1]['Close']},    Relative Volume: {round(bars.iloc[-1]['Volume']/bars.iloc[-1]['avg vol'], 2)}")
        atr = bars.iloc[-1]['ATR']
        st.text(f"Distance: {abs(distance)},    ATR: {round(atr, 2)},    Stop/ATR: {round(distance/atr,  2)}")
        st.text(f"Distance %: {distance_percent} %,   1 Sigma: {round(bars.iloc[-1]['std dev'], 2)} %,    Stop/Sigma: {round(distance_percent/bars.iloc[-1]['std dev'], 2)}")
