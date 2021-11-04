import mysql.connector
from sqlalchemy import create_engine
import sqlalchemy

import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import numpy as np
from ta import volatility

from PIL import Image
from datetime import datetime, timedelta

from io import BytesIO
import requests
import datetime as dt
##-------------------------------------------------SETTINGS-----------------------------------------------------------##
##----------LAYOUT SETUP----------
icon = Image.open('favicon.ico')
st.set_page_config(layout = 'wide', page_title = 'Watson 3', page_icon = '🔧')
st.markdown("<style>#MainMenu {visibility: hidden; } footer {visibility: hidden;}</style>", unsafe_allow_html=True)
st.markdown("<style>header {visibility: hidden;}</style>", unsafe_allow_html=True)
today = (datetime.today() - timedelta(hours = 5)).strftime('%Y-%m-%d')
risk = st.secrets['risk']  # <--------using static risk

##----------ALPHA VANTAGE---------
api_key = st.secrets['av_api_key']
def get_earnings(api_key, horizon, symbol=None):
    base_url= st.secrets['av_url']
    if symbol is not None:
        url = f'{base_url}function=EARNINGS_CALENDAR&symbol={symbol}&horizon={horizon}&apikey={api_key}'
        response = requests.get(url)
    else:
        url = f"{base_url}function=EARNINGS_CALENDAR&horizon={horizon}&apikey={api_key}"
        response = requests.get(url)
    return pd.read_csv(BytesIO(response.content))

##----------DATABASE SETUP--------
host = st.secrets['db_host']
user = st.secrets['db_user']
password = st.secrets['db_password']

@st.cache(hash_funcs = {sqlalchemy.engine.base.Engine: id}, ttl = 3600)
def db_connect(db):
    return create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{db}", pool_recycle=3600)


@st.cache(allow_output_mutation = True, hash_funcs = {sqlalchemy.engine.base.Engine: id}, ttl = 3600)
def run_query_cached(connection, query, index_col = None):
    return pd.read_sql_query(query, connection, index_col)

def run_query(connection, query, index_col = None):
    return pd.read_sql_query(query, connection, index_col)

def run_command(connection, query):
    connection.execute(query)

positions = db_connect('positions')
prices = db_connect('prices')
temp = db_connect('temp')

##----------OTHER-----------------
def isNowInTimePeriod(startTime, endTime, nowTime):
    if startTime < endTime:
        return nowTime >= startTime and nowTime <= endTime
    else:
        #Over midnight:
        return nowTime >= startTime or nowTime <= endTime

##---------------------------------------------DASHBOARD ELEMENTS-----------------------------------------------------##
##----------HEADER----------------
updated = run_query(positions, "SELECT Updated FROM updated")
one, two, three, four = st.columns([1,0.25,2.75,1])
with two:
    st.image(icon)
with three:
    #st.text("github.com/hieuimba/Watson-App")
    st.caption(f'Updated: {updated.iat[0, 0]}')

one, two, three = st.columns([1,3,1])
premarket = isNowInTimePeriod(dt.time(13,00), dt.time(13,30), dt.datetime.now().time())

with two:
    if premarket == True:
        option = st.radio('', options = ['Pre-market','Positions', 'PSC', 'Watchlist', 'Orders', 'Journal' , 'Sectors'])
    else:
        option = st.radio('', options = ['Positions', 'PSC', 'Watchlist', 'Orders', 'Journal', 'Sectors','Pre-market'])

st.markdown("<style>div.row-widget.stRadio > div{flex-direction:row;}</style>", unsafe_allow_html = True)
if option == 'Positions':
    st.markdown(f"<h1 style='text-align: center; color: black;'>Current Positions</h1>", unsafe_allow_html = True)
elif option == 'PSC':
    st.markdown(f"<h1 style='text-align: center; color: black;'>Position Size Calculator</h1>", unsafe_allow_html = True)
else:
    st.markdown(f"<h1 style='text-align: center; color: black;'>{option}</h1>", unsafe_allow_html = True)

##----------POSITIONS SCREEN------
if option == 'Positions':
    # Get data
    open_positions = run_query(positions, "SELECT * FROM open_positions", 'symbol')
    closed_orders = run_query(positions, "SELECT * FROM closed_orders", 'symbol')
    #closed_positions = closed_orders.copy()
    closed_positions = closed_orders[closed_orders.index != 'TSLA']

    # Calcs
    unrealized_pnl = '{0:.2f}'.format(open_positions['unrlzd p&l'].sum() / risk) + ' R'
    realized_pnl = '{0:.2f}'.format(closed_orders[closed_orders.index != 'TSLA']['rlzd p&l'].sum() / risk) + ' R'
    total_pnl = '{0:.2f}'.format((open_positions['unrlzd p&l'].sum() + closed_orders[closed_orders.index != 'TSLA']['rlzd p&l'].sum()) / risk,
                                 2) + ' R'
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
    closed_positions = closed_positions.drop(
        columns = ['action', 'type', 'status', 'time', 'price', 'filled qty', 'comm.'])
    closed_positions['entry'], closed_positions['stop'], closed_positions['target'], closed_positions[
        'unrlzd p&l'] = 0, 0, 0, 0  # not avaialbe yet
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
        open_positions.sort_values(by = 'unrlzd p&l', inplace = True, ascending = False)
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
        tradingview = open('html/tradingview.html', 'r', encoding = 'utf-8')
        source_code = tradingview.read()

        select = st.selectbox('', (selections))
        source_code = source_code.replace('DOW', select)
        components.html(source_code, height = 800)

##----------ORDERS SCREEN---------
if option == 'Orders':
    # Get data
    open_orders = run_query(positions, "SELECT * FROM open_orders", 'symbol')
    closed_orders = run_query(positions, "SELECT * FROM closed_orders", 'symbol')

    # Open orders
    '---'
    st.text(f'{len(open_orders)} open orders')
    st.dataframe(open_orders.style.format({'qty': '{0:.2f}',
                                           'price': '{0:.2f}'},
                                          na_rep = 'N/A'))

    # Closed orders
    st.text(f'{len(closed_orders)} closed orders')
    closed_orders.sort_values(by = 'status', inplace = True, ascending = False)
    closed_orders.drop(columns = ['rlzd p&l'], inplace = True)
    st.dataframe(closed_orders.style.format({'qty': '{0:.2f}',
                                             'price': '{0:.2f}',
                                             'filled at': '{0:.2f}',
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
    corr_matrix = pd.DataFrame()
    std_dev = pd.DataFrame()

    one, two = st.columns([1, 5])
    with one:
        options = st.radio('Select period:', options = ['1 M', '3 M', '6 M', '1 Y'],
                           help = '1 month = 21 trading days')
        if options == '1 M':
            period = 21
        elif options == '3 M':
            period = 63
        elif options == '6 M':
            period = 126
        elif options == '1 Y':
            period = 252

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
    corr_matrix = corr_matrix.style.background_gradient(cmap = 'Oranges', axis = None, low = -0.5,
                                                        subset = pd.IndexSlice[u[:-1], :])
    corr_matrix = corr_matrix.background_gradient(cmap = 'Greens', axis = None, subset = pd.IndexSlice[u[-1], :])
    st.table(corr_matrix.format(precision = 3))

##----------WATCHLIST SCREEN------
if option == 'Watchlist':
    '---'
    one,two = st.columns([1,2])
    with one:
        watchlist = run_query(positions, "SELECT * FROM watchlist", 'symbol')
        open_positions = run_query(positions, "SELECT * FROM open_positions", 'symbol')
        in_progress_symbols = open_positions.index.to_list()
        pullback = watchlist[watchlist['setup'] == 'pullback'].drop(columns = ['setup','qty'])
        pullback.replace(0, np.nan, inplace=True)
        pullback.sort_values(by = ['l/s','entry'], inplace = True, ascending = [True,False])
        all = pullback
        in_progress = pullback[pullback.index in in_progress_symbol]
        st.table(in_progress)
        st.table(pullback.style.format({'qty': '{0:.2f}',
                                                    'entry': '{0:.2f}',
                                                    'stop': '{0:.2f}',
                                                    'target': '{0:.2f}'},
                                                   na_rep='N/A'))

        user_input = st.text_input("Add, Modify, Delete")
        st.caption('Clear input when done')

        if user_input == '/help':
            st.info("/add - Add new record to list \n" 
                    "\n" "/mod - Modify a record \n" 
                    "\n" "/del - Delete a record \n"
                    "\n" "/help - Get help")

        elif user_input[0:4] == '/add':
            variable = user_input[5:len(user_input)].split(' ')
            if variable[0].upper() not in pullback.index.values.tolist():
                for i in range(0, len(variable)):
                    try:
                        variable[i] = float(variable[i])
                    except:
                        pass
                try:
                    symbol = variable[0].upper()
                    entry = variable[2]
                    stop = variable[3]
                    target = entry + entry - stop
                    distance = round(entry - stop, 2)
                    if distance == 0:
                        size = 0
                    else:
                        size = round(risk / abs(distance), 3)
                    try:
                        earnings = get_earnings(api_key,"6month",symbol).at[0,'reportDate']
                    except:
                        earnings = 'N/A'
                    variable.append(target)
                    variable.append('pullback')
                    variable.append(today)
                    variable.append(earnings)
                    variable.append(size)
                    add_cmd = f"INSERT INTO watchlist VALUES ('{symbol}', '{variable[1]}', {entry}, {stop}, '{target}', '{variable[5]}', '{variable[6]}', '{variable[7]}', '{variable[8]}')"
                    run_command(positions, add_cmd)
                    st.success(f"Added '{variable[0].upper()}'")
                except Exception as e:
                    st.error("Invalid command, use: \n"
                            "\n" "add/ [symbol]-[l/s]-[entry]-[stop]")
            else:
                st.error(f"Duplicate symbol, remove '{variable[0].upper()}' before continuing")

        elif user_input[0:4] == '/del':
            variable = user_input[5:len(user_input)].split(',')
            if variable[0].upper() in pullback.index.values.tolist():
                del_cmd = f"DELETE FROM watchlist WHERE symbol = '{variable[0].upper()}'"
                run_command(positions, del_cmd)
                st.success(f"Deleted '{variable[0].upper()}'")
            elif variable[0].upper() not in pullback.index.values.tolist():
                st.error(f"Cannot find '{variable[0].upper()}'")
            else:
                st.error("Invalid command, use: \n"
                         "\n" "del/ [symbol]")

        elif user_input[0:4] == '/mod':
            # variable = user_input[5:len(user_input)].split(' ')
            # if variable[0].upper() in pullback.index.values.tolist():
            #     if variable [1] in pullback.columns:
            #         for i in range(0, len(variable)):
            #             try:
            #                 variable[i] = float(variable[i])
            #             except:
            #                 pass
            #         if type(variable[2]) == float:
            #             mod_cmd = f"UPDATE watchlist SET {variable[1]}={variable[2]} WHERE symbol = '{variable[0].upper()}'"
            #             run_command(positions, mod_cmd)
            #             st.success(f"Modified '{variable[0].upper()}'")
            #         elif type(variable[2]) == str:
            #             mod_cmd = f"UPDATE watchlist SET {variable[1]}='{variable[2]}' WHERE symbol = '{variable[0].upper()}'"
            #             run_command(positions, mod_cmd)
            #             st.success(f"Modified '{variable[0].upper()}'")
            #         else:
            #             st.error("Invalid command, use: \n"
            #                      "\n" "mod/ [symbol]-[property]-[new value]")
            #     else:
            #         st.error("Invalid command, use: \n"
            #                  "\n" "mod/ [symbol]-[property]-[new value]")
            # elif variable[0].upper() not in pullback.index.values.tolist():
            #     st.error(f"Cannot find '{variable[0].upper()}'")
            # else:
            #     st.error("Invalid command, use: \n"
            #              "\n" "del/ [symbol]")
            st.warning("Under construction, try /del then /add")

        elif user_input == '':
            st.warning("Type a new command or type /help")
        else:
            st.error("Invalid command, try again or type /help")

    with two:
        selections = pullback.index.values.tolist()
        if len(selections) >0:
            selections = str(selections)[1:-1]

            tradingview = open('html/tradingview_watchlist.html', 'r', encoding='utf-8')
            source_code = tradingview.read()
            source_code = source_code.replace("'list'", selections)
            source_code = source_code.replace('DOW', pullback.index.values.tolist()[0])
            components.html(source_code, height=800)
        else:
            st.text('Watchlist is empty')

##----------CALC SCREEN-----------
if option == 'PSC':
    # Get data
    open_positions = run_query(positions, "SELECT * FROM open_positions", 'symbol')

    '---'
    symbol_list = run_query_cached(prices, "SELECT symbol FROM symbol_list")
    symbol_list = symbol_list['symbol'].to_list()

    beta_list = []
    matrix = pd.DataFrame()
    corr_matrix = pd.DataFrame()
    std_dev = pd.DataFrame()

    one, two, three = st.columns([2, 3, 1])
    with one:
        risk_options = [10, 20, 30, 50, 80, 100]
        risk = st.selectbox(label = '$ Risk', options = risk_options, index = 1)
        entry = st.number_input(label = 'Entry', value = 2.00, step = 0.1)
        stop = st.number_input(label = 'Stop', value = 1.00, step = 0.1)
        target = entry + (entry - stop)
        distance = round(entry - stop, 2)
        distance_percent = round(abs(distance) / entry, 2) * 100
        size = round(risk / abs(distance), 3)
        dollar_size = round(size * entry, 2)
        direction = 'Long' if distance > 0 else 'Short'
        st.number_input('Target', min_value = target, max_value = target, value = target)
        st.text(f'Direction: {direction}')
        st.subheader(f'Size: {size} share' if size == 1 else f'Size: {size} shares')
        ''
        st.text(f'$ Equivalent: $ {dollar_size}')
        st.subheader('R table:')
        price_range = [stop, stop + distance / 2, entry, entry + distance / 2, target, entry + distance * 2]
        price_range = pd.DataFrame(price_range, columns = ['Price'],
                                   index = ['-1 R', '-1.5 R', '0 R', '0.5 R', '1 R', '2 R']).T
        st.table(price_range.style.format(precision = 2))
    with three:
        options = st.radio('Select period:', options = ['1 M', '3 M', '6 M', '1 Y'], help = '1 month = 21 trading days')
        if options == '1 M':
            period = 21
        elif options == '3 M':
            period = 63
        elif options == '6 M':
            period = 126
        elif options == '1 Y':
            period = 252
    with two:
        symbol = st.multiselect('Select symbols:', options = symbol_list,
                                default = ['SPY'] + open_positions.index.values.tolist())

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
            if i == len(symbol) - 1:
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

        st.text(
            f"Symbol: {bars.iloc[-1]['Symbol']},    Name: {bars.iloc[-1]['Name']},    Sector: {bars.iloc[-1]['Sector']}")
        st.text(
            f"Last: {bars.iloc[-1]['Close']},    Relative Volume: {round(bars.iloc[-1]['Volume'] / bars.iloc[-1]['avg vol'], 2)}")
        atr = bars.iloc[-1]['ATR']
        st.text(f"Distance: {abs(distance)},    ATR: {round(atr, 2)},    Stop/ATR: {round(distance / atr, 2)}")
        st.text(
            f"Distance %: {distance_percent} %,   1 Sigma: {round(bars.iloc[-1]['std dev'], 2)} %,    Stop/Sigma: {round(distance_percent / bars.iloc[-1]['std dev'], 2)}")

        if bars.iloc[-1]['Symbol'] not in sector_list:
            earnings = get_earnings(api_key,"6month",bars.iloc[-1]['Symbol']).at[0,'reportDate']
            days_to_earnings = np.busday_count(datetime.today().strftime("%Y-%m-%d"), earnings) + 1
        else:
            earnings = 'N/A'
            days_to_earnings = 'N/A'

        st.text(f"Earnings date: {earnings},   Trading days till earnings: {days_to_earnings}")
        add_to_watchlist = st.button('Add to Watchlist')
        if add_to_watchlist:
            add_cmd = f"INSERT INTO watchlist VALUES ('{bars.iloc[-1]['Symbol']}', '{direction.lower()}', {entry}, {stop}, '{target}', 'pullback', '{today}', '{earnings}', '{size}')"
            run_command(positions, add_cmd)
            st.success(f"Added '{bars.iloc[-1]['Symbol']}' to watchlist")
            
##----------JOURNAL---------------
if option == 'Journal':
    journal = run_query(temp, "SELECT * FROM journal order by ID").tail(10)
    journal_full = run_query(temp, "SELECT * FROM journal_full order by ID").tail(5)
    journal = journal.drop(columns=['Quantity', 'Commission'])
    journal_full = journal_full.drop(columns=['Quantity'])
    journal['ID'] = journal['ID'].astype(str)
    journal_full['ID'] = journal_full['ID'].astype(str)
    journal = journal.set_index('ID')
    journal_full = journal_full.set_index('ID')
    one, two, three = st.columns([1, 3, 1])
    with two:
        st.text('Most recent trades')
        st.table(journal_full.style.format({'Entry': '{0:.2f}',
                                      'Stop': '{0:.2f}',
                                      'Target': '{0:.2f}',
                                      'Exit': '{0:.2f}',
                                      'ExitFilled': '{0:.2f}',
                                      'ATR': '{0:.2f}'},
                                     na_rep = 'N/A'))
        st.text('Most recent orders')
        st.table(journal.style.format({'Price': '{0:.2f}',
                                      'Fill at': '{0:.2f}',
                                      'Stop': '{0:.2f}',
                                      'Take Profit': '{0:.2f}',
                                      'ATR': '{0:.2f}'},
                                     na_rep = 'N/A'))
        
