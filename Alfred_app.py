import mysql.connector
from sqlalchemy import create_engine
import streamlit as st
import os

#user = os.environ.get('DB_USER')
#password = os.environ.get('DB_PASSWORD')
#host = os.environ.get('DB_HOST')

user = 'alfred'
password = 'Alfred:127.0.0.1'
host = '3.99.99.227'

database = 'prices'

engine = create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{database}", echo=False)
st.write('engine connected')
example = engine.execute(f"select * from etf_price limit 20")
st.write(example)
