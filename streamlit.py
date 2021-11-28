
# -*- coding: utf-8 -*-
# Copyright 2018-2019 Streamlit Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An example of showing geographic data."""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import pydeck as pdk
from streamlit_folium import folium_static
import folium

# SETTING PAGE CONFIG TO WIDE MODE
st.set_page_config(layout="wide")

# LOADING DATA
DATE_TIME = "date/time"
DATA_URL = (
    "gs://dva-sg-team105/processed_summary/processed_taxi_count.all.csv"
)

@st.cache(persist=True)
def load_data(nrows):
    data = pd.read_csv(DATA_URL, nrows=nrows)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis="columns", inplace=True)
    data[DATE_TIME] = pd.to_datetime(data[DATE_TIME])
    return data

data = load_data(100000)

# CREATING FUNCTION FOR MAPS

def map(data, lat, lon, zoom):
    st.write(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state={
            "latitude": lat,
            "longitude": lon,
            "zoom": zoom,
            "pitch": 50,
        },
        layers=[
            pdk.Layer(
                "HexagonLayer",
                data=data,
                get_position=["lon", "lat"],
                radius=100,
                elevation_scale=4,
                elevation_range=[0, 1000],
                pickable=True,
                extruded=True,
            ),
        ]
    ))

# LAYING OUT THE TOP SECTION OF THE APP
title_container = st.container()
with title_container:
    st.title("Cities in Motion")
    # st.subheader(
    # """
    # Tracking how demand for taxis has changed over the years in Singapore. 
    # """)
    st.write(
    """    
    Examining how demand for taxi has varied between a baseline period and current in Singapore. 
    """)

row1_1, row1_2 = st.columns((2,2))

with row1_1:
    st.subheader("Baseline Period")
with row1_2:
    st.subheader("Analysis Period")

# col2, col3 = st.rows(2)
# with col2:
row21, row22, row23, row24 = st.columns((1,1,1,1))
with row21:
    baseline_date_start = st.date_input("Baseline Start", value=data[DATE_TIME].min())
with row22:
    baseline_hour_start = st.slider("Baseline Hour Start", 0, 23)
with row23:
    analysis_date_start = st.date_input("Analysis Start", value=data[DATE_TIME].max())
with row24:
    analysis_hour_start = st.slider("Analysis Hour Star", 0, 23)    
# with col3:
row31, row32, row33, row34 = st.columns((1,1,1,1))
with row31:
    baseline_date_end = st.date_input("Baseline End", value=data[DATE_TIME].min())
with row32:
    baseline_hour_end = st.slider("Baseline Hour End", 0, 23)
with row33:
    analysis_date_end = st.date_input("Analysis End", value=data[DATE_TIME].max())
with row34:
    analysis_hour_end = st.slider("Analysis Hour End", 0, 23)    

# FILTERING DATA BY HOUR SELECTED
data = data[data[DATE_TIME].dt.hour == baseline_hour_start]

# LAYING OUT THE MIDDLE SECTION OF THE APP WITH THE MAPS
# row2_1, row2_2, row2_3, row2_4 = st.columns((2,1,1,1))

# # SETTING THE ZOOM LOCATIONS FOR THE AIRPORTS
# la_guardia= [40.7900, -73.8700]
# jfk = [40.6650, -73.7821]
# newark = [40.7090, -74.1805]
# zoom_level = 12
# midpoint = (np.average(data["lat"]), np.average(data["lon"]))

# with row2_1:
#     st.write("**All New York City from %i:00 and %i:00**" % (baseline_hour_start, (baseline_hour_start + 1) % 24))
#     map(data, midpoint[0], midpoint[1], 11)

# with row2_2:
#     st.write("**La Guardia Airport**")
#     map(data, la_guardia[0],la_guardia[1], zoom_level)

# with row2_3:
#     st.write("**JFK Airport**")
#     map(data, jfk[0],jfk[1], zoom_level)

# with row2_4:
#     st.write("**Newark Airport**")
#     map(data, newark[0],newark[1], zoom_level)

lat =  1.352083  #37.76
lon = 103.819836 #-122.4

row41, row42 = st.columns((1,1))
with row41:
    # map = folium.Map(location=[lat, lon], zoom_start=12, width="80%")
    # folium_static(map)
    st.image("taxi-availability-heatmap.png", use_column_width=True, caption=f"Taxi Demand between {baseline_date_start} and {baseline_date_end}")
with row42:
    st.image("nike-plus-run-map.jpg", use_column_width=True, caption=f"Taxi Demand between {analysis_date_start} and {analysis_date_end}")

# FILTERING DATA FOR THE HISTOGRAM
filtered = data[
    (data[DATE_TIME].dt.hour >= baseline_hour_start) & (data[DATE_TIME].dt.hour < (baseline_hour_start + 1))
    ]

hist = np.histogram(filtered[DATE_TIME].dt.minute, bins=24, range=(0, 24))[0]

chart_data = pd.DataFrame({"hour": range(24), "demand": hist})

# LAYING OUT THE HISTOGRAM SECTION

st.write("")

# st.write("**Breakdown of Taxi Demand**") # between %i:00 and %i:00**" % (baseline_hour_start, (baseline_hour_start + 23) % 24))

# st.altair_chart(alt.Chart(chart_data)
#     .mark_area(
#         interpolate='step-after',
#     ).encode(
#         x=alt.X("hour:Q", scale=alt.Scale(nice=False)),
#         y=alt.Y("demand:Q"),
#         tooltip=['hour', 'demand']
#     ).configure_mark(
#         opacity=0.2,
#         color='red'
#     ), use_container_width=True)

row51, row52 = st.columns((1,1))
changi_lat = 1.3480297
changi_lon = 103.9793892
overall_chart_data = pd.DataFrame(np.random.randn(1000, 2)/ [50, 50] + [lat, lon], columns= ['lat', 'lon'])
district_chart_data = pd.DataFrame(np.random.randn(500, 2)/ [150, 150] + [changi_lat, changi_lon], columns= ['lat', 'lon'])
drop_chart_data = pd.DataFrame(np.random.randn(300, 2), columns=['Baseline Projection', 'Actual'])
with row51:
    st.write("**Overall Taxi Demand - Projection versus Actual**")
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=11,
        pitch=50,
     ),
     layers=[
        pdk.Layer(
            'HexagonLayer',
            data=overall_chart_data,
            get_position='[lon, lat]',
            radius=200,
            elevation_scale=4,
            elevation_range=[0, 1000],
            pickable=True,
            extruded=True,
        ),
        pdk.Layer(
            'ScatterplotLayer',
            data=overall_chart_data,
            get_position='[lon, lat]',
            get_color='[200, 30, 0, 160]',
            get_radius=200,
         ),
     ],
    ))
    # st.line_chart(overall_chart_data, use_container_width=True)    
with row52:
    st.write("**Taxi Demand For Individual Districts**")        
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=pdk.ViewState(
        latitude=changi_lat, #lat,
        longitude=changi_lon, #long,
        zoom=12,
        pitch=50,
     ),
     layers=[
        pdk.Layer(
            'HexagonLayer',
            data=district_chart_data,
            get_position='[lon, lat]',
            radius=200,
            elevation_scale=4,
            elevation_range=[0, 1000],
            pickable=True,
            extruded=True,
        ),
        pdk.Layer(
            'ScatterplotLayer',
            data=district_chart_data,
            get_position='[lon, lat]',
            get_color='[200, 30, 0, 160]',
            get_radius=200,
         ),
     ],
    ))
    option = st.selectbox("District", ("Changi Airport", "Choa Chu Kang", "CBD", "Toa Payoh"))
    # st.line_chart(district_chart_data, use_container_width=True)
# with row53:
#     st.write("**Biggest Drop in Demand in:** Changi Airport ")
#     # option = st.selectbox("District", ("Choa Chu Kang", "Changi Airport", "CBD", "Toa Payoh"))
#     st.line_chart(drop_chart_data, use_container_width=True)        
# with row54:
#     st.write("**Trends**")
#     st.write("1. **Overall Fleet Occupancy**:")
#     st.write("    a. Baseline: **58.52%**")
#     st.write("    b. Current: **48.36%**")