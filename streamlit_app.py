import mysql.connector
from sqlalchemy import create_engine
import sqlalchemy

import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import numpy as np
import matplotlib

from ta import volatility

st.set_page_config(layout = 'wide', page_title = 'Alfred 4', page_icon = '🎩')
st.write('hello')
genre = st.radio(
"What's your favorite movie genre",
('Comedy', 'Drama', 'Documentary'))

risk = st.secrets['risk']  # <--------using static risk

##----------DATABASE SETUP--------
host = st.secrets['db_host']
user = st.secrets['db_user']
password = st.secrets['db_password']
db = "prices"
create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{db}")
