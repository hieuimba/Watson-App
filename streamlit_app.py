import mysql.connector
from sqlalchemy import create_engine
import sqlalchemy

import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import numpy as np
import matplotlib

from ta import volatility

st.write('hello')
genre = st.radio(
"What's your favorite movie genre",
('Comedy', 'Drama', 'Documentary'))
