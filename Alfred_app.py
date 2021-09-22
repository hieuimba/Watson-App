import mysql.connector
from sqlalchemy import create_engine
import streamlit
import os

user = os.environ.get('DB_USER')
password = os.environ.get('DB_PASSWORD')
host = os.environ.get('DB_HOST')
database = 'prices'

engine = create_engine(f"mysql://{user}:{password}@{host}/{database}", echo=False)
st.write('engine connected')
example = engine.execute(f"select * from etf_price limit 20")
st.write(example)