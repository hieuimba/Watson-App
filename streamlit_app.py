import mysql.connector
from sqlalchemy import create_engine
import sqlalchemy

import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import numpy as np
from ta import volatility
import altair as alt

import plotly.express as px
import plotly.graph_objects as go

from PIL import Image
from datetime import datetime, timedelta

from io import BytesIO
import requests
import datetime as dt

##-------------------------------------------------SETTINGS-----------------------------------------------------------##
# ----------SECRETS---------------
RISK = st.secrets['risk']
FAVICON_PATH = "favicon.ico"
API_KEY = st.secrets['av_api_key']
API_BASE_URL = st.secrets['av_url']
DB_HOST = st.secrets['db_host']
DB_USER = st.secrets['db_user']
DB_PASSWORD = st.secrets['db_password']
TRADINGVIEW = 'html/tradingview.html'
JOURNAL_PASSWORD = st.secrets['journal_password']

today = datetime.today() - timedelta(hours=0)
today_string = today.strftime('%Y-%m-%d')

# ----------LAYOUT SETUP----------
HIDE_FOOTER = "<style>#MainMenu {visibility: hidden; } footer {visibility: hidden;}</style>"
HIDE_SETTINGS = "<style>header {visibility: hidden;}</style>"
page_icon = Image.open(FAVICON_PATH)

st.set_page_config(layout='wide', page_title='Watson 3', page_icon='🔧')  # page_icon
st.markdown(HIDE_FOOTER, unsafe_allow_html=True)
st.markdown(HIDE_SETTINGS, unsafe_allow_html=True)


# ----------ALPHA VANTAGE---------
def get_earnings(api_key, horizon, symbol=None):
    if symbol is not None:
        url = f'{API_BASE_URL}function=EARNINGS_CALENDAR&symbol={symbol}&horizon={horizon}&apikey={api_key}'
        response = requests.get(url)
    else:
        url = f"{API_BASE_URL}function=EARNINGS_CALENDAR&horizon={horizon}&apikey={api_key}"
        response = requests.get(url)
    return pd.read_csv(BytesIO(response.content))


# ----------DATABASE SETUP--------
@st.cache(hash_funcs={sqlalchemy.engine.base.Engine: id}, ttl=7200)
def connect_db(database):
    return create_engine(f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{database}", pool_recycle=7200)

@st.cache(allow_output_mutation=True, hash_funcs={sqlalchemy.engine.base.Engine: id}, ttl=3600)
def run_query_cached(connection, query, index_col=None):
    return pd.read_sql_query(query, connection, index_col)


def run_query(connection, query, index_col=None):
    return pd.read_sql_query(query, connection, index_col)


def run_command(connection, query):
    connection.execute(query)

POSITIONS_DB = connect_db('positions')
PRICES_DB = connect_db('prices')
JOURNAL_DB = connect_db('journal')
REPORT_DB = connect_db('report')

# ----------PLOTLY TABLES---------
from plotly.colors import n_colors
def create_table(df, suffix = None, col_width = None, align = 'left', heatmap = False, exclude = 2):
    header_height = 30
    cell_height = 30
    green = 'rgb(144,238,144)'
    yellow = 'rgb(255,255,224)'
    red = 'rgb(240,128,128)'
    watson = 'rgba(120, 0, 62, 1)'
    cell_list_list = []
    color_list = []

    for col in df.reset_index().transpose().values.tolist():
        cell_list = []
        cell_color = []
        for cell in col:
            try:
                cell_list.append(np.round(cell, 2))
            except:
                cell_list.append(cell)
        if heatmap == True:
            colors_low = n_colors(green, yellow, 51, colortype='rgb')
            colors_high = n_colors(yellow, red, 51, colortype='rgb')
            if all(isinstance(cell, float) for cell in cell_list):
                for cell in cell_list[:-exclude]:
                    cell = cell * 100
                    cell_int = abs(int(cell))
                    if cell_int == 100:
                        cell_color.append(watson)
                    elif cell_int <= 50:
                        cell_color.append(colors_low[cell_int])
                    elif 50 < cell_int:
                        cell_color.append(colors_high[cell_int-50])
                for cell in cell_list[-exclude:]:
                    cell_color.append('white')
            elif all(isinstance(cell, str) for cell in cell_list):
                cell_color = ['white' for cell in cell_list]
        else:
            cell_color = ['white' for cell in cell_list]
        color_list.append(cell_color)
        cell_list_list.append(cell_list)

    header = ['' if wd == 'index' else wd for wd in list(df.reset_index().columns)]
    fig = go.Figure(data=[go.Table(
        columnwidth=col_width,
        header=dict(values=header,
                    fill_color=watson,
                    line_color='dimgrey',
                    align='left',
                    height=header_height,
                    font=dict(color='white', size=15)),
        cells=dict(values=cell_list_list,
                   fill_color=color_list,
                   line_color='dimgrey',
                   align=align,
                   suffix=suffix,
                   height=cell_height,
                   font=dict(size=15)))
    ])
    def calc_table_height(df, base=header_height, height_per_row=cell_height, char_limit=30,
                          height_padding=cell_height):
        total_height = 0 + base
        for x in range(df.shape[0]):
            total_height += height_per_row
        for y in range(df.shape[1]):
            if len(str(df.iloc[x][y])) > char_limit:
                total_height += height_padding
        return total_height + 30
    #st.write(calc_table_height(df))
    fig.update_layout(margin=dict(l=1, r=1, t=0, b=0), height=calc_table_height(df))
    return fig

# ----------PREMARKET-------------
def is_in_time_period(start_time, end_time, now_time):
    if start_time < end_time:
        return now_time >= start_time and now_time <= end_time
    else:
        # Over midnight:
        return now_time >= start_time or now_time <= end_time

pre_market = is_in_time_period(
    dt.time(8, 00), dt.time(8, 30), dt.datetime.now().time())

##---------------------------------------------DASHBOARD -------------------------------------------------------------##
# ----------HEADER----------------
HORIZONTAL_RADIO = "<style>div.row-widget.stRadio > div{flex-direction:row;}</style>"
POSITIONS_HEADING = "<h1 style='text-align: center; color: black;'>Current Positions</h1>"
PSC_HEADING = "<h1 style='text-align: center; color: black;'>Position Size Calculator</h1>"

updated = run_query(POSITIONS_DB, "SELECT Updated FROM updated")

one, two, three, four = st.columns([1, 0.25, 2.75, 1])
with two:
    st.image(page_icon)
with three:
    st.write("")
    st.caption(f'Updated: {updated.iat[0, 0]}')

one, two, three = st.columns([1, 3, 1])
with two:
    if pre_market == True:
        screen = st.radio('', options=[
            'Pre-market', 'Positions', 'PSC', 'Watchlist', 'Scanner', 'Reports', 'Journal'])
    else:
        screen = st.radio('', options=[
            'Positions', 'PSC', 'Watchlist', 'Scanner', 'Reports', 'Journal'])
st.markdown(HORIZONTAL_RADIO, unsafe_allow_html=True)
OTHER_HEADING = f"<h1 style='text-align: center; color: black;'>{screen}</h1>"

if screen == 'Positions':
    st.markdown(POSITIONS_HEADING, unsafe_allow_html=True)
elif screen == 'PSC':
    st.markdown(PSC_HEADING, unsafe_allow_html=True)
else:
    st.markdown(OTHER_HEADING, unsafe_allow_html=True)

# ----------POSITIONS SCREEN------
if screen == 'Positions':
    open_positions = run_query(
        POSITIONS_DB, "SELECT * FROM open_positions", 'Symbol')
    closed_orders = run_query(
        POSITIONS_DB, "SELECT * FROM closed_orders", 'Symbol')
    closed_positions = run_query(
        POSITIONS_DB, "SELECT * FROM closed_positions", 'Symbol')

    # Calcs
    unrealized_pnl = open_positions['Unrlzd P&L'].sum() / RISK
    unrealized_pnl = format(unrealized_pnl, '.2f') + ' R'

    realized_pnl = closed_orders['Rlzd P&L'].sum() / RISK
    realized_pnl = format(realized_pnl, '.2f') + ' R'

    total_pnl = (open_positions['Unrlzd P&L'].sum() + closed_orders['Rlzd P&L'].sum()) / RISK
    total_pnl = format(total_pnl, '.2f') + ' R'

    total_open_risk = open_positions['Open Risk'].sum() / RISK
    total_open_risk = format(total_open_risk, '.2f') + ' R'

    # Format open positions table
    open_positions['Rlzd P&L'] /= RISK
    open_positions['Unrlzd P&L'] /= RISK
    open_positions['Open Risk'] /= RISK
    open_positions = open_positions.sort_values(
        by='Unrlzd P&L', ascending=False)
    open_positions = open_positions.drop(columns=['Qty'])
    open_positions = open_positions.rename(columns={"Rlzd P&L": "Rlzd P/L", "Unrlzd P&L": "Unrlzd P/L"})

    # Format closed positions table
    closed_positions['Rlzd P&L'] /= RISK
    closed_positions['Unrlzd P&L'] /= RISK
    closed_positions = closed_positions.sort_values(
        by='Rlzd P&L', ascending=False)
    closed_positions = closed_positions.drop(columns=['Qty'])
    closed_positions = closed_positions.rename(columns={"Rlzd P&L": "Rlzd P/L", "Unrlzd P&L": "Unrlzd P/L"})

    # Positions summary
    one, two, three = st.columns([1, 3, 1])
    with two:
        '---'
    one, two, three, four = st.columns([1, 4.5/2, 1.5/2, 1])
    with two:
        st.subheader(f'Current P&L: {total_pnl}')
        st.write(f'Unrealized: {unrealized_pnl}')
        st.write(f'Realized: {realized_pnl}')
    with three:
        st.subheader('Risk:')
        st.write(f'Total open risk: {total_open_risk}')
        st.write(f'Expected Shortfall: N/A')
        #st.write(f'Portfolio Variance: N/A')

    # Positions tables
    one, two, three = st.columns([1, 3, 1])
    with two:
        '---'
        st.write(f'{len(open_positions)} trade in progress' if len(open_positions) == 1 else
                 f'{len(open_positions)} trades in progress')
        if len(open_positions) > 0:
            open_posisions_table = create_table(open_positions,
                                                suffix = ['','','','','','',' R',' R','R'],
                                                align = ['left']*2 + ['right']*6)
            st.plotly_chart(open_posisions_table, use_container_width=True, config = {'staticPlot': True})

        if len(closed_positions) > 0:
            st.write(f'{len(closed_positions)} closed trade' if len(closed_positions) == 1 else
                    f'{len(closed_positions)} closed trades')
            closed_posisions_table = create_table(closed_positions,
                                                  suffix=['', '', '', '', '', '', ' R', ' R'],
                                                  align=['left']*2 + ['right']*6)
            st.plotly_chart(closed_posisions_table, use_container_width=True, config={'staticPlot': True})

    one, two, three = st.columns([1, 3, 1])
    with two:
         # TradingView Chart
        chart_symbols = list(open_positions.index.values) + \
                       list(closed_positions.index.values) + ['SPY']
        tradingview = open(
            TRADINGVIEW, 'r', encoding='utf-8')
        source_code = tradingview.read()
        source_code = source_code.replace('DOW', chart_symbols[0])
        source_code = source_code.replace("'list'", str(chart_symbols)[1:-1])
        components.html(source_code, height=700)


    # Orders
        order_expander = st.expander(label='Orders')
        with order_expander:
            open_orders = run_query(POSITIONS_DB, "SELECT * FROM open_orders", 'Symbol')

            # Open orders
            st.write(f'{len(open_orders)} open orders')
            if len(open_orders) > 0:
                open_orders.drop(columns=['Filled Qty', 'Qty'], inplace=True)
                open_orders = open_orders[['Action', 'Type', 'Price', 'Status']]
                st.plotly_chart(create_table(open_orders, align=['left']*2 + ['right'] +['left']),
                                use_container_width=True, config={'staticPlot': True})
            # Closed orders
            st.write(f'{len(closed_orders)} closed orders')
            if len(closed_orders) > 0:
                closed_orders.sort_values(by='Status', inplace=True, ascending=False)
                closed_orders.drop(columns=['Rlzd P&L', 'Filled Qty', 'Qty'], inplace=True)
                closed_orders = closed_orders[['Action', 'Type', 'Price', 'Filled At', 'Status', 'Time']]
                st.plotly_chart(create_table(closed_orders, align=['left']*3 + ['right']*2 +['left']*2),
                                use_container_width=True, config={'staticPlot': True})

# ----------CALC SCREEN-----------
if screen == 'PSC':
    # Get data
    open_positions = run_query(
        POSITIONS_DB, "SELECT * FROM open_positions", 'Symbol')
    '---'
    symbol_list = run_query_cached(PRICES_DB, "SELECT * FROM symbol_list")
    etf_list = symbol_list[symbol_list['Sec_Type'] == 'ETF']
    symbol_list = sorted(symbol_list['Symbol'].to_list())
    etf_list = etf_list['Symbol'].to_list()

    beta_list = []
    matrix = pd.DataFrame()
    corr_matrix = pd.DataFrame()
    std_dev = pd.DataFrame()

    one, two, three = st.columns([2, 3, 1])
    with one:
        risk_options = [10, 20, 30, 50, 80, 100]
        risk = st.selectbox(label='$ Risk', options=risk_options, index=1)
        entry = st.number_input(label='Entry', value=2.00, step=0.1)
        stop = st.number_input(label='Stop', value=1.00, step=0.1)
        target = entry + (entry - stop)
        distance = round(entry - stop, 2)
        distance_percent = round(abs(distance) / entry, 2) * 100
        size = round(risk / abs(distance), 3)
        dollar_size = round(size * entry, 2)
        direction = 'Long' if distance > 0 else 'Short'
        st.number_input('Target', min_value=target,
                        max_value=target, value=target)
        st.write(f'Direction: {direction}')
        st.subheader(f'Size: {size} share' if size ==
                                              1 else f'Size: {size} shares')
        ''
        st.write(f"Cash Equivalent: $ {dollar_size}")
        st.subheader('R table:')
        price_range = [stop, stop + distance / 2, entry,
                       entry + distance / 2, target, entry + distance * 2]
        price_range = pd.DataFrame(price_range, columns=['Price'],
                                   index=['-1 R', '-1.5 R', '0 R', '0.5 R', '1 R', '2 R']).T
        st.plotly_chart(create_table(price_range, align=['left'] + ['right'] * 6),
                        use_container_width=True, config={'staticPlot': True})

    with three:
        options = st.radio('Select period:', options=[
            '1 M', '3 M', '6 M', '1 Y'], help='1 month = 21 trading days')
        if options == '1 M':
            period = 21
        elif options == '3 M':
            period = 63
        elif options == '6 M':
            period = 126
        elif options == '1 Y':
            period = 252
    with two:
        if 'SPY' in open_positions.index.values.tolist():
#             new_list = open_positions.index.values.tolist().remove('SPY').insert(0, 'SPY')
            symbol = st.multiselect('Select symbols:', options=symbol_list,
                            default= open_positions.index.values.tolist().remove('SPY').insert(0, 'SPY'))
        else:
            symbol = st.multiselect('Select symbols:', options=symbol_list,
                                    default=['SPY'] + open_positions.index.values.tolist())
        #st.subheader('Portfolio Correlation')
        spy = run_query_cached(PRICES_DB, "SELECT * FROM etf_price WHERE symbol = 'SPY'")
        spy['return%'] = spy['Close'].pct_change(1) * 100
        spy = spy.tail(period)
        spy['var'] = spy['return%'].var()

        for i in range(0, len(symbol)):
            if symbol[i] in etf_list:
                bars = run_query_cached(
                    PRICES_DB, f"SELECT * FROM etf_price WHERE symbol = '{symbol[i]}'")
                bars = bars.fillna('N/A')
            else:
                bars = run_query_cached(
                    PRICES_DB, f"SELECT * FROM stock_price WHERE symbol = '{symbol[i]}'")
                bars = bars.fillna('N/A')

            bars['return%'] = bars['Close'].pct_change(1) * 100
            if i == len(symbol) - 1:
                bars['std dev'] = bars['return%'].rolling(21).std()
                bars['ATR'] = volatility.AverageTrueRange(bars['High'], bars['Low'], bars['Close'],
                                                          window=21).average_true_range()
                bars['avg vol'] = bars['Volume'].rolling(21).mean()
            bars = bars.tail(period)
            matrix[f'{symbol[i]}'] = bars['return%'].values
            corr_matrix = matrix.corr()

            bars['bm_return%'] = spy['return%'].to_list()
            cov_df = bars[['return%', "bm_return%"]].cov()
            bm_var = spy.iloc[-1]['var']
            beta = cov_df.iloc[1, 0] / bm_var
            beta_list.append(beta)

        temp = pd.DataFrame(index=symbol)
        temp['Beta-M'] = beta_list
        temp = temp.T
        temp2 = pd.DataFrame(index=symbol)
        temp2['Beta-S'] = 0
        temp2 = temp2.T
        corr_matrix = corr_matrix.append(temp)
        corr_matrix = corr_matrix.append(temp2)

        matrix_table = create_table(corr_matrix, align=['left'] + ['right'], heatmap = True)
        st.plotly_chart(matrix_table, use_container_width=True, config={'staticPlot': True})

        st.subheader(f"Ticker Info: {bars.iloc[-1]['Symbol']}")
        st.write(f"Name: {bars.iloc[-1]['Name']}, Sector: {bars.iloc[-1]['Sector']}")
        st.write(f"Last: {bars.iloc[-1]['Close']}, Relative Volume: {round(bars.iloc[-1]['Volume'] / bars.iloc[-1]['avg vol'], 2)}")
        atr = bars.iloc[-1]['ATR']
        st.write(
            f"Distance: {abs(distance)},    ATR: {round(atr, 2)},    Stop/ATR: {round(distance / atr, 2)}")
        st.write(
            f"Distance %: {distance_percent} %,   1 Sigma: {round(bars.iloc[-1]['std dev'], 2)} %,    Stop/Sigma: {round(distance_percent / bars.iloc[-1]['std dev'], 2)}")
        try:
            if bars.iloc[-1]['Symbol'] not in etf_list:
                earnings = get_earnings(
                    API_KEY, "6month", bars.iloc[-1]['Symbol']).at[0, 'reportDate']
                days_to_earnings = np.busday_count(
                    today_string, earnings) + 1
            else:
                earnings = 'N/A'
                days_to_earnings = 'N/A'
        except:
            earnings = 'Error'
            days_to_earnings = 'Error'

        st.write(
            f"Earnings date: {earnings},   Trading days till earnings: {days_to_earnings}")
        add_to_watchlist = st.button('Add to Watchlist')
        if add_to_watchlist:
            add_cmd = f"INSERT INTO watchlist VALUES ('{bars.iloc[-1]['Symbol']}', '{direction.lower()}', {entry}, {stop}, '{target}', 'pullback', '{today_string}', '{earnings}', '{size}')"
            run_command(POSITIONS_DB, add_cmd)
            st.success(f"Added '{bars.iloc[-1]['Symbol']}' to watchlist")

# ----------WATCHLIST SCREEN------
if screen == 'Watchlist':
    watchlist = run_query(POSITIONS_DB, "SELECT * FROM watchlist", 'Symbol')
    open_positions = run_query(POSITIONS_DB, "SELECT * FROM open_positions", 'Symbol')
    '---'
    one, two = st.columns([1, 2])
    with one:
        in_progress_symbols = open_positions.index.to_list()

        pullback = watchlist[watchlist['Setup'] ==
                             'pullback'].drop(columns=['Setup', 'Qty'])
        pullback.replace(0, np.nan, inplace=True)
        pullback.sort_values(by=['L/S', 'Symbol'],
                             inplace=True, ascending=[True, True])

        all = pullback
        in_progress_boolean = pullback.index.isin(in_progress_symbols)
        in_progress = all[in_progress_boolean]
        setting_up_boolean = ~pullback.index.isin(in_progress_symbols)
        setting_up = all[setting_up_boolean]
        inbox = pullback[pullback['Entry'].isna()]

        watchlist_type = st.radio("Select watchlist:", ("Setting Up", "In Progress", "All"), index=0)
        if watchlist_type == "All" and len(all) > 0:
            all_table = create_table(all,
                                     col_width = [20, 18, 18, 18, 18, 25, 25],
                                     align=['left','left'] + ['right']*5)
            st.plotly_chart(all_table, use_container_width=True, config={'staticPlot': True})
        if watchlist_type == "In Progress" and len(in_progress) > 0:
            in_progress_table = create_table(in_progress,
                                     col_width = [20, 18, 18, 18, 18, 25, 25],
                                     align=['left','left'] + ['right']*5)
            st.plotly_chart(in_progress_table, use_container_width=True, config={'staticPlot': True})
        if watchlist_type == "Setting Up" and len(setting_up) > 0:
            setting_up = setting_up[setting_up['Entry'].notna()]
            setting_up_table = create_table(setting_up,
                                     col_width = [20, 18, 18, 18, 18, 25, 25],
                                     align=['left','left'] + ['right']*5)
            st.plotly_chart(setting_up_table, use_container_width=True, config={'staticPlot': True})
        if watchlist_type == "Inbox" and len(inbox) > 0:
            inbox_table = create_table(inbox,
                                     col_width = [20, 18, 18, 18, 18, 25, 25],
                                     align=['left','left'] + ['right']*5)
            st.plotly_chart(inbox_table, use_container_width=True, config={'staticPlot': True})

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
                        size = round(RISK / abs(distance), 3)
                    try:
                        earnings = get_earnings(
                            API_KEY, "6month", symbol).at[0, 'reportDate']
                    except:
                        earnings = 'N/A'
                    variable.append(target)
                    variable.append('pullback')
                    variable.append(today_string)
                    variable.append(earnings)
                    variable.append(size)
                    add_cmd = f"INSERT INTO watchlist VALUES ('{symbol}', '{variable[1]}', {entry}, {stop}, '{target}', '{variable[5]}', '{variable[6]}', '{variable[7]}', '{variable[8]}')"
                    run_command(POSITIONS_DB, add_cmd)
                    st.success(f"Added '{variable[0].upper()}'")
                except Exception as e:
                    st.error("Invalid command, use: \n"
                             "\n" "add/ [symbol]-[l/s]-[entry]-[stop]")
            else:
                st.error(
                    f"Duplicate symbol, remove '{variable[0].upper()}' before continuing")

        elif user_input[0:4] == '/del':
            variable = user_input[5:len(user_input)].split(',')
            if variable[0].upper() in pullback.index.values.tolist():
                del_cmd = f"DELETE FROM watchlist WHERE symbol = '{variable[0].upper()}'"
                run_command(POSITIONS_DB, del_cmd)
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
            #             run_command(POSITIONS_DB, mod_cmd)
            #             st.success(f"Modified '{variable[0].upper()}'")
            #         elif type(variable[2]) == str:
            #             mod_cmd = f"UPDATE watchlist SET {variable[1]}='{variable[2]}' WHERE symbol = '{variable[0].upper()}'"
            #             run_command(POSITIONS_DB, mod_cmd)
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
        if watchlist_type == "All":
            selections = all.index.values.tolist()
        if watchlist_type == "In Progress":
            selections = in_progress.index.values.tolist()
        if watchlist_type == "Setting Up":
            selections = setting_up.index.values.tolist()
        if watchlist_type == "Inbox":
            selections = inbox.index.values.tolist()
        if len(selections) > 0:
            selections = str(selections)[1:-1]

            tradingview = open(
                TRADINGVIEW, 'r', encoding='utf-8')
            source_code = tradingview.read()
            source_code = source_code.replace("'list'", selections)
            source_code = source_code.replace(
                'DOW', pullback.index.values.tolist()[0])
            components.html(source_code, height=800)
        else:
            st.write('Watchlist is empty')

# ----------JOURNAL---------------
if screen == 'Journal':
    journal_full = run_query_cached(JOURNAL_DB, "SELECT * FROM journal_full order by ID")
    journal_cmt = run_query_cached(JOURNAL_DB, "SELECT * FROM journal_cmt order by ID limit 200")
    journal_full['ID'] = journal_full['ID'].astype(str)
    journal_full = journal_full.set_index('ID')
    journal_full['PnL'] = round(journal_full['PnL'] / RISK, 2)

    one, two, three = st.columns([1, 6, 1])
    with two:
        '---'
    one, two, three, four = st.columns([1, 2, 4, 1])
    with two:
        select_view = st.radio('Select view:', options=['Summary', 'Table', 'List', 'Gallery'], index=0)
    with three:
        last_n_trade = st.radio('Last:', ('All', '50 trades', '25 trades', '10 trades'), index=1)
        if last_n_trade == 'All':
            n = len(journal_full)
        if last_n_trade == '50 trades':
            n = 50
        if last_n_trade == '25 trades':
            n = 25
        if last_n_trade == '10 trades':
            n = 10
        journal_full = journal_full[::-1].head(n)

    if select_view == 'Summary':
        one, two, three = st.columns([1, 6, 1])
        with two:
            text_input_container = st.empty()
            password = text_input_container.text_input("Enter password", type="password")

        if password == JOURNAL_PASSWORD:
            text_input_container.empty()

            journal_full = journal_full.drop(columns=['Signal'])
            journal_full = journal_full.dropna()
            journal_full = journal_full.reset_index()

            one, two, three, four = st.columns([1, 2, 4, 1])
            with two:
                last_n_pnl = journal_full['PnL'].sum()
                last_n_pnl = format(last_n_pnl, '.2f') + ' R'
                st.subheader(f'Cummulative P&L: {last_n_pnl}')

            one, two, three = st.columns([1, 6, 1])
            with two:
                bar_chart = alt.Chart(journal_full).mark_bar(size=5).encode(
                    x=alt.X('ID', sort=journal_full[::-1]['ID'].to_list(), axis=alt.Axis(title='')),
                    y=alt.Y('PnL', axis=alt.Axis(title='P/L')),
                    color=alt.condition(
                        alt.datum.PnL > 0,
                        alt.value('green'),
                        alt.value('red')
                    )
                ).configure_view(strokeWidth=0).configure_axis(grid=False)
                st.altair_chart(bar_chart, use_container_width=True)

                journal_full['Rolling PnL'] = np.cumsum(journal_full[::-1]['PnL'])
                line_chart = alt.Chart(journal_full).mark_line(size=3).encode(
                    x=alt.X('ID', sort=journal_full[::-1]['ID'].to_list(), axis=alt.Axis(title='')),
                    y=alt.Y('Rolling PnL', axis=alt.Axis(title='Rolling P&L')),
                    color=alt.value("#FFAA00")
                ).configure_view(strokeWidth=0).configure_axis(grid=False)
                st.altair_chart(line_chart, use_container_width=True)
                st.subheader('Statistics')

            one, two, three, four, five = st.columns([1, 2, 2, 2, 1])
            with two:
                win_count = journal_full['PnL'][journal_full['PnL'] > 0].count()
                loss_count = journal_full['PnL'][journal_full['PnL'] <= 0].count()
                win_percentage = round(win_count / (win_count + loss_count) * 100, 2)
                win_rate = win_count / (win_count + loss_count)

                total_win = journal_full['PnL'][journal_full['PnL'] > 0].sum()
                total_loss = journal_full['PnL'][journal_full['PnL'] <= 0].sum()

                avg_win = round(total_win / win_count, 2)
                avg_loss = round(total_loss / loss_count, 2)

                expectancy = round(win_rate * avg_win + (1 - win_rate) * avg_loss, 2)

                st.write(f'Average gain/loss: {expectancy} R')
                st.write(f'Win rate: {win_percentage} %')
                st.write(f'Average winning trade: {avg_win} R')
                st.write(f'Average losing trade: {avg_loss} R')
                st.write(f'Number of winning trades: {win_count}')
                st.write(f'Number of losing trades: {loss_count}')
            with three:
                win_max = journal_full['PnL'].max()
                loss_max = journal_full['PnL'].min()
                profit_factor = round(total_win / total_loss, 2)
                std_dev = round(journal_full['PnL'].std(), 2)

                journal_full['Win'] = journal_full['PnL'] > 0
                journal_full['start_of_streak'] = journal_full.Win.ne(journal_full['Win'].shift())
                journal_full['streak_id'] = journal_full['start_of_streak'].cumsum()
                journal_full['streak_counter'] = journal_full.groupby('streak_id').cumcount() + 1

                win_filter = journal_full[journal_full['Win'] == True]
                loss_filter = journal_full[journal_full['Win'] == False]
                max_con_win = win_filter['streak_counter'].max()
                max_con_loss = loss_filter['streak_counter'].max()

                st.write(f'Profit factor: {profit_factor}')
                st.write(f'Trade P&L standard deviation: {std_dev} R')
                st.write(f'Largest gain: {win_max} R')
                st.write(f'Largest loss: {loss_max} R')

                st.write(f'Max consecutive wins: {max_con_win}')
                st.write(f'Max consecutive loss: {max_con_loss}')
            with four:
                total_commission = round(journal_full['Comm'].sum() / RISK, 2)

                conditions = [(journal_full['L/S'] == 'Long'), (journal_full['L/S'] == 'Short')]
                slippage_long = (journal_full['Entry'] - journal_full['EntryFilled'] + journal_full['ExitFilled'] -
                                 journal_full['Exit']) * journal_full['Qty']
                slippage_short = (journal_full['EntryFilled'] - journal_full['Entry'] + journal_full['Exit'] -
                                  journal_full['ExitFilled']) * journal_full['Qty']
                values = [slippage_long, slippage_short]
                journal_full['Slippage'] = np.select(conditions, values)
                total_slippage = round(journal_full['Slippage'].sum() / RISK, 2)

                st.write(f'Average Holding Time: N/A')
                st.write(f'Total commission: {total_commission} R')
                st.write(f'Total slippage: {total_slippage} R')
        elif password == "":
            pass
        else:
            one, two, three = st.columns([1, 6, 1])
            with two:
                st.error("Incorrect password")

    if select_view == 'Table':
        journal_full = journal_full.drop(columns=['Signal'])
        one, two, three = st.columns([1, 6, 1])
        with two:
            text_input_container = st.empty()
            password = text_input_container.text_input("Enter password", type="password")

        if password == JOURNAL_PASSWORD:
            text_input_container.empty()

            total_pnl = journal_full['PnL'].sum()
            total_pnl = format(total_pnl, '.2f') + ' R'

            def get_pnl_between_two_dates(start_date, end_date):
                after_start_date = journal_full['Date Close'] >= start_date
                before_end_date = journal_full['Date Close'] <= end_date
                between_two_dates = after_start_date & before_end_date
                filter = journal_full.loc[between_two_dates]
                pnl = filter['PnL'].sum()
                return format(pnl, '.2f') + ' R'

            end_date = pd.to_datetime(today)
            start_date_mtd = pd.to_datetime(today.replace(day=1))
            start_date_ytd = pd.to_datetime(today.replace(month=1, day=1))
            start_date_3m = pd.to_datetime(today - timedelta(90))
            start_date_6m = pd.to_datetime(today - timedelta(180))
            start_date_9m = pd.to_datetime(today - timedelta(270))

            month_to_date_pnl = get_pnl_between_two_dates(start_date_mtd, end_date)
            year_to_date_pnl = get_pnl_between_two_dates(start_date_mtd, end_date)
            three_month_pnl = get_pnl_between_two_dates(start_date_3m, end_date)
            six_month_pnl = get_pnl_between_two_dates(start_date_6m, end_date)
            nine_month_pnl = get_pnl_between_two_dates(start_date_9m, end_date)

            one, two, three, four = st.columns([1, 1.5, 4.5, 1])
            with two:
                st.subheader(f'Month-to-Date: {month_to_date_pnl}')
                st.write(f'Year-to-Date: {year_to_date_pnl}')
                st.write(f'Total: {total_pnl}')
            with three:
                st.subheader(f'3 Month: {three_month_pnl}')
                st.write(f'6 Month: {six_month_pnl}')
                st.write(f'9 Month: {nine_month_pnl}')
            one, two, three = st.columns([1, 6, 1])
            with two:
                journal_full_table = create_table(journal_full, align=['right'] + ['left']*4 + ['right']*9)
                st.plotly_chart(journal_full_table, use_container_width=True, config={'staticPlot': True})
        elif password == "":
            pass
        else:
            one, two, three = st.columns([1, 6, 1])
            with two:
                st.error("Incorrect password")

    if select_view == 'List':
        one, two, three = st.columns([1, 6, 1])
        with two:
            text_input_container = st.empty()
            password = text_input_container.text_input("Enter password", type="password")

            if password == JOURNAL_PASSWORD:
                text_input_container.empty()

                for i in journal_full.index.to_list():
                    i_int = int(float(i))
                    symbol = journal_full.at[i, 'Symbol']
                    direction = journal_full.at[i, 'L/S']
                    date_open = journal_full.at[i, 'Date Open']
                    date_close = journal_full.at[i, 'Date Close']
                    pnl = journal_full.at[i, 'PnL']

                    record = journal_full.loc[journal_full.index == i].drop(columns=['Entry', 'Exit'])
                    record = record.rename({"EntryFilled": "Entry'", "ExitFilled": "Exit'", "PnL": "P&L"},
                                           axis='columns')

                    if np.isnan(pnl):
                        label = f"{i_int}. {symbol} {direction} - In Progress"
                    elif pnl > 0:
                        label = f"{i_int}. {symbol} {direction} +{abs(pnl)} R"
                    else:
                        label = f"{i_int}. {symbol} {direction} -{abs(pnl)} R"

                    record = record[
                        ['Date Open', 'Date Close', 'Symbol', 'L/S', 'Qty', "Entry'", 'Stop', 'Target',
                         "Exit'", 'P&L', 'Signal']]
                    #record = record.assign(hack='').set_index('hack')
                    record_expander = st.expander(label=label)
                    with record_expander:
                        record = record.rename(columns={"P&L": "P/L"})
                        record_table = create_table(record,
                                                    col_width=[15, 25, 25]+[20]*9,
                                                    align=['right'] + ['left', 'left'] + ['right'] * 6)
                        st.plotly_chart(record_table, use_container_width=True, config={'staticPlot': True})

                        comment = journal_cmt.at[i_int - 1, 'Comment']
                        if comment == None:
                            st.write("")
                        else:
                            st.write(comment)

                        st.image(f'https://journal-screenshot.s3.ca-central-1.amazonaws.com/{i_int}_{symbol}.png',
                                 use_column_width='auto')

                        user_input = st.text_input(f"{i_int}. Type comment: ")
                        st.caption('Clear input when done')

                        if user_input != '':
                            confirm = st.text_input(f"{i_int}. Enter password", type="password")
                            if confirm == JOURNAL_PASSWORD:
                                add_cmd = f"""UPDATE journal_cmt SET Comment = "{user_input}" WHERE ID = {i_int}"""
                                run_command(JOURNAL_DB, add_cmd)
                                st.success("Comment added")
                            elif confirm == '':
                                pass
                            else:
                                st.error("Incorrect password")
            elif password == "":
                pass
            else:
                st.error("Incorrect password")

    if select_view == 'Gallery':
        one, two, three = st.columns([1, 6, 1])
        with two:
            text_input_container = st.empty()
            password = text_input_container.text_input("Enter password", type="password")

        if password == JOURNAL_PASSWORD:
            text_input_container.empty()

            one, two, three, four = st.columns([1, 5, 5, 1])
            with two:
                for i in journal_full.index.to_list():
                    i_int = int(float(i))
                    if i_int % 2 == 0:
                        symbol = journal_full.at[i, 'Symbol']
                        st.image(f'https://journal-screenshot.s3.ca-central-1.amazonaws.com/{i_int}_{symbol}.png',
                                 use_column_width='auto')
            with three:
                for i in journal_full.index.to_list():
                    i_int = int(float(i))
                    if i_int % 2 != 0:
                        symbol = journal_full.at[i, 'Symbol']
                        st.image(f'https://journal-screenshot.s3.ca-central-1.amazonaws.com/{i_int}_{symbol}.png',
                                 use_column_width='auto')
        elif password == "":
            pass
        else:
            one, two, three = st.columns([1, 6, 1])
            with two:
                st.error("Incorrect password")

if screen == 'Reports':
    mkt_report = run_query_cached(REPORT_DB, "SELECT * FROM mkt_report")
    stock_analysis = run_query_cached(REPORT_DB, "SELECT * FROM stock_analysis")
    mkt_report_updated = run_query_cached(REPORT_DB, "SELECT * FROM updated")
    report_date = mkt_report_updated.iat[0, 0]

    one, two, three = st.columns([1, 6, 1])
    with two:
        # Open orders
        '---'
        mkt_report_tab = f'Market Report - {report_date} '
        report_select = st.radio('Select report:', options=[mkt_report_tab, 'US Sectors'])

    if report_select == mkt_report_tab:
        bar_chart = alt.Chart(mkt_report).mark_bar(size=10).encode(
            x=alt.X('Market', sort=mkt_report['Market'].to_list(), axis=alt.Axis(title='', labelAngle = -45)),
            y=alt.Y('SSpike', axis=alt.Axis(title='Sigma Spike')),
            color=alt.condition(
                alt.datum.SSpike > 0,
                alt.value('green'),
                alt.value('red')
            )
        ).configure_view(strokeWidth=0)

        mkt_report = mkt_report.set_index('Symbol')

        one, two, four = st.columns([1, 6, 1])
        with two:
            st.subheader('Broad Market Review')

        one, two, three, four = st.columns([1, 3, 3, 1])
        with two:
            mkt_report_table_1 = create_table(mkt_report.head(14),
                                            suffix=['', '', '', '', ' %', '', '', ''],
                                            col_width = [50, 100, 50, 50, 50, 50, 50, 50],
                                            align=['left','left'] + ['right']*6)
            st.plotly_chart(mkt_report_table_1, use_container_width=True, config = {'staticPlot': True})
        with three:
            mkt_report_table_2 = create_table(mkt_report.tail(14),
                                            suffix=['', '', '', '', ' %', '', '', ''],
                                            col_width = [50, 100, 50, 50, 50, 50, 50, 50],
                                            align=['left','left'] + ['right']*6)
            st.plotly_chart(mkt_report_table_2, use_container_width=True, config = {'staticPlot': True})

        one, two, three = st.columns([1, 6, 1])
        with two:
            st.altair_chart(bar_chart, use_container_width=True)
            st.subheader('Stock Analysis')

        one, two, three, four, five = st.columns([1, 3, 1.5, 1.5, 1])
        with two:
            st.write(f"Looking at {stock_analysis['Total'].iloc[0]} active US tickers")
            stock_analysis = stock_analysis.set_index('L/S')

            sigma_spike_df = stock_analysis[['SS1', 'SS2', 'SS3', 'SS4', 'SS5', 'SS5plus']]
            ss_up = px.pie(values=sigma_spike_df.values.tolist()[0],
                           names = ['< 1', '1-2', '2-3', '3-4', '4-5', '> 5'],
                           color_discrete_sequence=px.colors.sequential.Greens_r)
            ss_down = px.pie(values=sigma_spike_df.values.tolist()[1],
                             names = ['< 1', '1-2', '2-3', '3-4', '4-5', '> 5'],
                             color_discrete_sequence=px.colors.sequential.Reds_r)
            ss_up.update_traces(sort=False)
            ss_down.update_traces(sort=False)
            ss_up.update_layout(margin = dict(l=0,r=0,t=0,b=0), width= 300, height =300)
            ss_down.update_layout(margin = dict(l=0,r=0,t=0,b=0), width= 300, height =300)

            advance_decline = stock_analysis[['A/D']]
            total_advance_decline = advance_decline['A/D'].sum()
            total_advance = advance_decline.at['Long','A/D']
            total_decline = advance_decline.at['Short','A/D']
            advance_decline = advance_decline.T.reset_index()
            advance_decline_chart = px.bar(advance_decline, x = ['Long', 'Short'], y = 'index', barmode = 'stack', color_discrete_sequence =['green','red'])
            advance_decline_chart.add_annotation(x=0, y=1,
                                                   text= f"{total_advance} Advancing",
                                                   showarrow=False,
                                                   yshift=5)
            advance_decline_chart.add_annotation(x=0, y=1,
                                                   text=f"{round(total_advance/(total_advance_decline) * 100,2)}%",
                                                   showarrow=False,
                                                   yshift=-23, xshift= 23, font=dict(color = 'white'))
            advance_decline_chart.add_annotation(x=total_advance_decline , y=1,
                                                   text= f"{total_decline} Declining",
                                                   showarrow=False,
                                                   yshift=5)
            advance_decline_chart.add_annotation(x=total_advance_decline , y=1,
                                                   text=f"{round(total_decline/(total_advance_decline) * 100,2)}%",
                                                   showarrow=False,
                                                   yshift=-23, xshift= -23, font=dict(color = 'white'))
            advance_decline_chart.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=50,
                                                  showlegend = False, plot_bgcolor = 'white',
                                                  hovermode =False,
                                                  xaxis={'visible': False, 'showticklabels': False, 'fixedrange' : True},
                                                  yaxis={'visible': False, 'showticklabels': False, 'fixedrange' : True})

            close_up_down = stock_analysis[['Up/Down']]
            total_close_up_down = close_up_down['Up/Down'].sum()
            total_up = close_up_down.at['Long', 'Up/Down']
            total_down = close_up_down.at['Short', 'Up/Down']
            close_up_down = close_up_down.T.reset_index()
            close_up_down_chart = px.bar(close_up_down, x = ['Long', 'Short'], y = 'index', barmode = 'stack', color_discrete_sequence =['green','red'])
            close_up_down_chart.add_annotation(x=0, y=1,
                                                 text=f"{total_up} Closed ↑",
                                                 showarrow=False,
                                                 yshift=5)
            close_up_down_chart.add_annotation(x=0, y=1,
                                                 text=f"{round(total_up/(total_close_up_down) * 100,2)}%",
                                                 showarrow=False,
                                                 yshift=-23, xshift= 23, font=dict(color = 'white'))
            close_up_down_chart.add_annotation(x=total_close_up_down, y=1,
                                                 text=f"{total_down} Closed ↓",
                                                 showarrow=False,
                                                 yshift=5)
            close_up_down_chart.add_annotation(x=total_close_up_down, y=1,
                                                 text=f"{round(total_down/(total_close_up_down) * 100,2)}%",
                                                 showarrow=False,
                                                 yshift=-23, xshift= -23, font=dict(color = 'white'))
            close_up_down_chart.layout.xaxis.fixedrange = True
            close_up_down_chart.layout.yaxis.fixedrange = True
            close_up_down_chart.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=50,
                                                showlegend=False, plot_bgcolor='white',
                                                hovermode=False,
                                                xaxis={'visible': False, 'showticklabels': False, 'fixedrange' : True},
                                                yaxis={'visible': False, 'showticklabels': False, 'fixedrange' : True})

            new_high_low = stock_analysis[['NewH/L']]
            total_new_high_low = new_high_low['NewH/L'].sum()
            total_new_high = new_high_low.at['Long', 'NewH/L']
            total_new_low = new_high_low.at['Short', 'NewH/L']
            new_high_low = new_high_low.T.reset_index()
            new_high_low_chart = px.bar(new_high_low, x = ['Long', 'Short'], y = 'index', barmode = 'stack', color_discrete_sequence =['green','red'])
            new_high_low_chart.add_annotation(x=0, y=1,
                                               text=f"{total_new_high} New High",
                                               showarrow=False,
                                               yshift=5)
            new_high_low_chart.add_annotation(x=total_new_high_low, y=1,
                                               text=f"{total_new_low} New Low",
                                               showarrow=False,
                                               yshift=5)
            new_high_low_chart.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=50,
                                              showlegend=False, plot_bgcolor='white',
                                              xaxis={'visible': False, 'showticklabels': False, 'fixedrange': True},
                                              yaxis={'visible': False, 'showticklabels': False, 'fixedrange': True})

            st.plotly_chart(advance_decline_chart, use_container_width=True, config = {'staticPlot': True})
            st.plotly_chart(close_up_down_chart, use_container_width=True, config = {'staticPlot': True})
            st.plotly_chart(new_high_low_chart, use_container_width=True, config = {'staticPlot': True})
        with three:
            st.write(f'Long sigma distribution (of {total_advance})')
            st.plotly_chart(ss_up, use_container_width=True)
        with four:
            st.write(f'Short sigma distribution (of {total_decline})')
            st.plotly_chart(ss_down, use_container_width=True)


    if report_select == 'US Sectors':
        sector_list = ['SPY', 'XLE', 'XLI', 'XLK', 'XLY', 'XLF',
                       'XLB', 'XLP', 'XLV', 'XLU', 'XLRE', 'XLC', 'IWM', 'QQQ']
        beta_list = []
        matrix = pd.DataFrame()
        corr_table = pd.DataFrame()
        corr_matrix = pd.DataFrame()
        std_dev = pd.DataFrame()

        one, two, thee = st.columns([1, 6, 1])
        with two:
            st.subheader('Sector Correlations')
        one, two, three, four = st.columns([1, 1, 5, 1])
        with two:
            options = st.radio('Select period:', options=['1 M', '3 M', '6 M', '1 Y'],
                               help='1 month = 21 trading days')
            if options == '1 M':
                period = 21
            elif options == '3 M':
                period = 63
            elif options == '6 M':
                period = 126
            elif options == '1 Y':
                period = 252

        # Translation table
        with three:
            sector_name = ['SPX 500', 'Energy', 'Industrial', 'Tech.', 'Cons Disc.',
                           'Financial', 'Materials', 'Cons Staples', 'Health Care', 'Utilities',
                           'Real Estate', 'Comm.', 'Russell 2000', 'QQQ Trust']
            sector_trans = pd.DataFrame(data=sector_name, index=sector_list)
            sector_trans = sector_trans.T.set_index('SPY')
            st.plotly_chart(create_table(sector_trans), use_container_width=True, config={'staticPlot': True})

        # Correlation table
        one, two, three = st.columns([1, 6, 1])
        with two:
            spy = run_query_cached(
                PRICES_DB, "SELECT * FROM etf_price WHERE symbol = 'SPY'")
            spy['return%'] = spy['Close'].pct_change(1) * 100

            for i in range(0, len(sector_list)):
                sector = run_query_cached(
                    PRICES_DB, f"SELECT * FROM etf_price WHERE symbol = '{sector_list[i]}'")

                sector['return%'] = sector['Close'].pct_change(1) * 100
                corr_table[f'{sector_list[i]}'] = sector['return%'].rolling(21).corr(spy['return%'])
                corr_table['Date'] = spy['Date']

                spy_short = spy.tail(period)
                spy_short['var'] = spy_short['return%'].var()

                sector_short = sector.tail(period)
                matrix[f'{sector_list[i]}'] = sector_short['return%'].values
                corr_matrix = matrix.corr()
                sector_short['bm_return%'] = spy_short['return%'].to_list()
                cov_df = sector_short[['return%', "bm_return%"]].cov()
                bm_var = spy_short.iloc[-1]['var']
                beta = cov_df.iloc[1, 0] / bm_var
                beta_list.append(beta)

            temp = pd.DataFrame(index=sector_list)
            temp['Beta'] = beta_list
            temp = temp.T
            corr_matrix = corr_matrix.append(temp)

            matrix_table = create_table(corr_matrix, align=['left'] + ['right'], heatmap=True, exclude=1)
            st.plotly_chart(matrix_table, use_container_width=True, config={'staticPlot': True})
            #st.plotly_chart(create_table(corr_table), use_container_width=True, config={'staticPlot': True})

            st.subheader('One-month Rolling Correlations')
            corr_line = px.line(corr_table.tail(252-21), x='Date', y=sector_list, color_discrete_sequence= ['#696969']+ px.colors.qualitative.Plotly)
            corr_line.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=500,
                                    plot_bgcolor='white',
                                    legend_title_text='Sectors',
                                    xaxis={'title':'','tickangle':45, 'zeroline': True},
                                    yaxis={'title':'Correlation','fixedrange': True, 'zeroline': True, 'zerolinecolor':'dimgrey'})
            #corr_line.update_xaxes(ticks="outside", tickwidth=2, tickcolor='crimson', ticklen=10)
            corr_line.update_xaxes(nticks=30)
            corr_line.update_xaxes(showline=True, linewidth=1, linecolor='dimgrey')
            corr_line.update_yaxes(showline=True, linewidth=1, linecolor='dimgrey')

            st.plotly_chart(corr_line, use_container_width=True, config={'staticPlot': False})
            #st.line_chart(corr_table.set_index('Date'))

if screen == 'Scanner':
    one, two , three = st.columns([1,3,1])
    with two:
        '---'
        st.info('Coming soon')
