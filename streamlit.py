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

import datetime as dt
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import pydeck as pdk
from streamlit_folium import folium_static
import folium
import geopandas as gpd
import json
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon

# SETTING PAGE CONFIG TO WIDE MODE
st.set_page_config(layout="wide")

# LOADING DATA
MIN_DATE_TIME = datetime(2016, 9, 16, 13, 0, 0)
MIN_COVID_DATE_TIME = datetime(2020, 4, 1, 0, 0, 0)
MAX_DATE_TIME = datetime(2021, 10, 16, 13, 0, 0)
COUNTRY_GEO = 'data/region1.geojson'
EXCLUDED_DISTRICTS = ['CHANGI BAY', 'LIM CHU KANG', 'SIMPANG']

st.sidebar.header("Filter by time")

@st.cache(persist=True)
def load_taxi_count():
    # processed_fname = f'gs://dva-sg-team105/processed_summary/processed_taxi_count.all.csv'
    year_dfs = [pd.read_csv(f'./data/analysis/processed_taxi_count.{year}.csv', index_col=0) for year in range(2016, 2022)]
    _df = pd.concat(year_dfs, axis=0)        
    
    # preprocessing
    _df = _df.reset_index().set_index('filename')
    idx = set(_df.index)
    idx_to_dt_map = {x:datetime.strptime(str(x), "%Y%m%d%H%M%S") for x in idx}

    # drop noisy data
    idx_to_drop = [i for i in idx if (i < 20160916130000) 
                   or ((i >= 20171016110000) & (i <= 20171129090000))]
    _df.drop(idx_to_drop, axis=0, inplace=True)

    _df.index = _df.index.map(idx_to_dt_map)

    return _df

full_data = load_taxi_count()
districts = sorted(list(set(full_data.region) - set(EXCLUDED_DISTRICTS)))

@st.cache(persist=True)
def load_taxi_locations():
    # fname = f'gs://dva-sg-team105/processed/2021/taxi_region.20211001000000.csv'
    fname = './data/processed/2021/taxi_region.20211001000000.csv' #not available

    df = pd.read_csv(fname, index_col=0)
    st.write(df)
    # add geometry
    df['geometry'] = df['geometry'].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(df, crs='epsg:4326')
    return gdf
# taxi_locations = load_taxi_locations()

@st.cache(persist=True)
def load_country_gdf():
    # fname = f'gs://dva-sg-team105/region1.geojson'
    fname = './data/region1.geojson'

    with open(fname, "rb") as f:
        country_json = json.load(f)    
    country_gdf = gpd.GeoDataFrame.from_features(country_json)
    country_gdf["geometry"] = [MultiPolygon(feature) if type(feature) != Polygon else feature for feature in country_gdf["geometry"]]
    # TUAS, SOUTHERN ISLANDS, WESTERN WATER CATCHMENT and other districts are GeometryCollection geometries in the source file. They don't play well with GeoJsonTooltip. Casting them all to
    # MultiPolygon to ensure the GeoJson tooltip works. For more info, see: https://github.com/python-visualization/folium/issues/929
    return country_gdf

country_gdf = load_country_gdf()

def filter_data(full_data, baseline_date_start, analysis_date_start, hour_of_day, time_period, time_frequency):
    def date_to_datetime(t):
        return datetime(t.year, t.month, t.day)

    def get_time_delta(time_period, time_frequency):
        p = int(time_period)
        if time_frequency.lower() == 'hours':
            return timedelta(hours=p)
        elif time_frequency.lower() == 'days':
            return timedelta(days=p)
        elif time_frequency.lower() == 'weeks':
            return timedelta(weeks=p)
        elif time_frequency.lower() == 'months':
            return timedelta(months=p*30)  # just a hack
        elif time_frequency.lower() == 'months':
            return timedelta(years=p*365)  # just a hack

    baseline_from = date_to_datetime(baseline_date_start) + timedelta(hours=int(hour_of_day))
    baseline_to = baseline_from + get_time_delta(time_period, time_frequency)
    if baseline_to >= datetime(2020, 4, 1):
        baseline_to = datetime(2020, 4, 1)

    # st.write(baseline_from, baseline_to)  # debug

    analysis_from = date_to_datetime(analysis_date_start) + timedelta(hours=int(hour_of_day))
    analysis_to = analysis_from + get_time_delta(time_period, time_frequency)
    if analysis_to >= datetime(2021, 10, 1):
        analysis_to =datetime(2021, 10, 1)

    # st.write(analysis_from, analysis_to)  # debug

    baseline_data = full_data.loc[baseline_from:baseline_to].copy()
    baseline_data = baseline_data.groupby('region').mean().round().reset_index()  # take mean across all hourly data
    # st.write(baseline_data)  # debug

    analysis_data = full_data.loc[analysis_from:analysis_to].copy()
    analysis_data = analysis_data.groupby('region').mean().round().reset_index()  # take mean across all hourly data
    # st.write(analysis_data)  # debug

    return baseline_data, analysis_data


def create_folium_choropleth(taxi_count_df, country_geo, country_gdf):
    # center on Singapore
    m = folium.Map(location=[1.3572, 103.8207], zoom_start=11)
    bins = list(range(0, 1000, 100))
    # taxi_count_df 
    # country_geo    
    # country_geo = country_geo["geometry"].apply(lambda x: Multipolygon(x))

    # change country_gdf such that taxi count appears on tooltip
    data_on_date = taxi_count_df.copy()  # deepcopy
    country_gdf_on_date = country_gdf.copy()  # deepcopy
    districts_on_date = sorted(list(set(data_on_date.region.tolist())))
    name_to_namecount_map = {d:d + ' ' + str(data_on_date.loc[data_on_date.region == d, 'taxi_count'].values[0]) for d in districts_on_date}
    data_on_date['region'] = data_on_date.region.map(name_to_namecount_map)
    data_on_date.dropna(subset=['region'], inplace=True)
    country_gdf_on_date['name'] = country_gdf_on_date.name.map(name_to_namecount_map)
    country_gdf_on_date.dropna(subset=['name'], inplace=True)    

    choropleth = folium.Choropleth(
        geo_data=country_gdf_on_date.to_json(),
        # name="choropleth",
        data=data_on_date,
        columns=["region", "taxi_count"],
        key_on="properties.name",
        fill_color="YlOrRd",
        nan_fill_color="black",
        nan_fill_opacity=0.5,
        fill_opacity=0.7,
        line_opacity=0.8,
        bins=bins,
        legend_name="Taxi Count",
    ).add_to(m)
    choropleth.geojson.add_child(folium.GeoJsonTooltip(
        fields=["name"], #, "description"],
        aliases=['District'] #, 'Taxi Count']
        ))

    # call to render Folium map in Streamlit
    folium_static(m, width=750)

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


# STREAMLIT CODE BELOW #

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
    Examining how demand for taxi has varied because of Covid in Singapore. 
    """)

st.subheader("Summary (Islandwide)")

with st.expander("Search Parameters", expanded=True):
    row21, row22, row23, row24, row25 = st.columns((1,1,1,1,1))
    with row21:
        #Delta of (Baseline date + hour + for the next time unit - baseline date + hour)
        baseline_date_start = st.date_input("Pre-Covid Period Starts On", value=MIN_DATE_TIME)
    with row22:
        analysis_date_start = st.date_input("Covid Period Starts On", value=MIN_COVID_DATE_TIME)
    with row23:
        hour_of_day =  st.number_input("Hour of the Day (0-23)", value=6, min_value=0, max_value=23) # st.time_input("Hour of the Day", )#, datetime.time(13,00))
    with row24:
        time_period = st.number_input("For the next", value=10, min_value=1)
    with row25:
        time_frequency = st.selectbox("Time Unit", ("Hours", "Days", "Weeks", "Months", "Years")) #, "Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"))


# FILTERING DATA BY INPUTS
baseline_data, analysis_data = filter_data(full_data, baseline_date_start, analysis_date_start, hour_of_day, time_period, time_frequency)


lat =  1.352083  #37.76
lon = 103.819836 #-122.4

row41, row42 = st.columns((1,1))
with row41:
    _date = datetime.strftime(baseline_date_start, "%Y-%m-%d")    
    st.markdown(f"##### Pre-Covid: Taxi Availability as on {_date}")
    create_folium_choropleth(baseline_data, COUNTRY_GEO, country_gdf)    
    # st.text(f'Nu {_date}')
with row42:
    _analysis_date = datetime.strftime(analysis_date_start, "%Y-%m-%d")    
    st.markdown(f'##### Post-Covid: Taxi Availability as on {_analysis_date}')
    create_folium_choropleth(analysis_data, COUNTRY_GEO, country_gdf)

# FILTERING DATA FOR THE HISTOGRAM
# filtered = data[
#     (data[DATE_TIME].dt.hour >= baseline_hour_start) & (data[DATE_TIME].dt.hour < (baseline_hour_start + 1))
#     ]

# hist = np.histogram(filtered[DATE_TIME].dt.minute, bins=24, range=(0, 24))[0]

# chart_data = pd.DataFrame({"hour": range(24), "demand": hist})

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

st.subheader("District Analysis")

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
    option = st.selectbox("District", districts, index=districts.index('CHANGI'))
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
