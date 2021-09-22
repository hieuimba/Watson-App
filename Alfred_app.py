import mysql.connector
from sqlalchemy import create_engine
import streamlit as st

host = st.secrets["db_host"]
user = st.secrets["db_user"]
password = st.secrets["db_password"]
database = 'prices'

engine = create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{database}", echo=False)
st.write('engine connected')
example = engine.execute(f"select * from etf_price limit 20")
st.write(example.fetchall())
