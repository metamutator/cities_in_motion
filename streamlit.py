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
import plotly.express as px
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


# st.sidebar.header("Filter by time")


def date_to_datetime(t):
    # helper method
    return datetime(t.year, t.month, t.day)


@st.cache(persist=True, allow_output_mutation=True, suppress_st_warning=True)
def load_taxi_count():
    # processed_fname = f'gs://dva-sg-team105/processed_summary/processed_taxi_count.all.csv'
    year_dfs = [pd.read_csv(f'./data/analysis/processed_taxi_count.{year}.csv', index_col=0) for year in
                range(2016, 2022)]
    _df = pd.concat(year_dfs, axis=0)

    # preprocessing
    _df = _df.reset_index().set_index('filename')
    idx = set(_df.index)
    idx_to_dt_map = {x: datetime.strptime(str(x), "%Y%m%d%H%M%S") for x in idx}

    # drop noisy data
    idx_to_drop = [i for i in idx if (i < 20160916130000)
                   or ((i >= 20171016110000) & (i <= 20171129090000))]
    _df.drop(idx_to_drop, axis=0, inplace=True)

    _df.index = _df.index.map(idx_to_dt_map)

    return _df


full_data = load_taxi_count()
districts = sorted(list(set(full_data.region) - set(EXCLUDED_DISTRICTS)))


@st.cache(persist=True, allow_output_mutation=True, suppress_st_warning=True)
def load_taxi_locations():
    # fname = f'gs://dva-sg-team105/processed/2021/taxi_region.20211001000000.csv'
    fname = './data/processed/2021/taxi_region.20211001000000.csv'  # not available

    df = pd.read_csv(fname, index_col=0)
    st.write(df)
    # add geometry
    df['geometry'] = df['geometry'].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(df, crs='epsg:4326')
    return gdf


# taxi_locations = load_taxi_locations()

@st.cache(persist=True, allow_output_mutation=True, suppress_st_warning=True)
def load_country_gdf():
    fname = COUNTRY_GEO

    with open(fname, "rb") as f:
        country_json = json.load(f)
    country_gdf = gpd.GeoDataFrame.from_features(country_json)
    country_gdf["geometry"] = [MultiPolygon(feature) if type(feature) != Polygon else feature for feature in
                               country_gdf["geometry"]]
    # TUAS, SOUTHERN ISLANDS, WESTERN WATER CATCHMENT and other districts are GeometryCollection geometries in the source file. They don't play well with GeoJsonTooltip. Casting them all to
    # MultiPolygon to ensure the GeoJson tooltip works. For more info, see: https://github.com/python-visualization/folium/issues/929
    country_gdf["lat"] = country_gdf.centroid.x
    country_gdf['long'] = country_gdf.centroid.y
    return country_gdf


country_gdf = load_country_gdf()

@st.cache(persist=True, allow_output_mutation=True, suppress_st_warning=True)
def filter_data(full_data, baseline_date_start, analysis_date_start, hour_of_day, time_period, time_frequency):
    def get_time_delta(time_period, time_frequency):
        p = int(time_period)
        if time_frequency.lower() == 'hours':
            return timedelta(hours=p)
        elif time_frequency.lower() == 'days':
            return timedelta(days=p)
        elif time_frequency.lower() == 'weeks':
            return timedelta(weeks=p)

    baseline_from = date_to_datetime(baseline_date_start) + timedelta(hours=int(hour_of_day))
    baseline_to = baseline_from + get_time_delta(time_period, time_frequency)
    if baseline_to >= datetime(2020, 4, 1):
        baseline_to = datetime(2020, 4, 1)

    # st.write(baseline_from, baseline_to)  # debug

    analysis_from = date_to_datetime(analysis_date_start) + timedelta(hours=int(hour_of_day))
    analysis_to = analysis_from + get_time_delta(time_period, time_frequency)
    if analysis_to >= datetime(2021, 10, 1):
        analysis_to = datetime(2021, 10, 1)

    # st.write(analysis_from, analysis_to)  # debug

    baseline_data = full_data.loc[baseline_from:baseline_to].copy()
    baseline_data["hour"] = baseline_data.index.hour
    baseline_data["hour"] = baseline_data["hour"].astype(int)
    baseline_data = baseline_data[baseline_data["hour"] == int(hour_of_day)]
    baseline_data.drop('hour', axis=1, inplace=True)
    baseline_data = baseline_data.groupby('region').mean().round().reset_index()  # take mean across all hourly data
    # st.write(baseline_data)  # debug

    analysis_data = full_data.loc[analysis_from:analysis_to].copy()
    analysis_data["hour"] = analysis_data.index.hour
    analysis_data["hour"] = analysis_data["hour"].astype(int)
    analysis_data = analysis_data[analysis_data["hour"] == int(hour_of_day)]
    analysis_data.drop('hour', axis=1, inplace=True)
    analysis_data = analysis_data.groupby('region').mean().round().reset_index()  # take mean across all hourly data
    # st.write(analysis_data)  # debug

    return baseline_data, analysis_data

@st.cache(persist=True, allow_output_mutation=True, suppress_st_warning=True)
def taxigraph(dataset, region, hour, startdate, enddate):
    """
    dataset: full_data = load_taxi_count()
    region: expects string eg. 'ANG MO KIO'
    hour: hour of the day, integer [0:23]
    startdate: 'Pre-Covid Period Starts On' date
    enddate: 'Covid Period Starts On' date
    """
    def date_to_datetime(t):
        return datetime(t.year, t.month, t.day)

    basedata = full_data.copy()

    basedata = basedata.loc[str(startdate):str(enddate)]  # date
    basedata = basedata[basedata.index.hour == hour]  # hour
    if region != "All":
        basedata = basedata.loc[basedata.region == region]  # region
    
    basedata = basedata.reset_index()
    basedata[ 'rolling_average' ] = basedata.taxi_count.rolling(90).mean()
    return basedata

def create_folium_choropleth(taxi_count_df, country_geo, country_gdf, max_count):
    # center on Singapore
    m = folium.Map(location=[1.3572, 103.8207], zoom_start=11)

    max_count_rounded = int((max_count // 100) + 2) * 100  # like math.ceil
    bins = list(range(0, max_count_rounded, max_count_rounded // 10))

    # change country_gdf such that taxi count appears on tooltip
    data_on_date = taxi_count_df.copy()  # deepcopy
    country_gdf_on_date = country_gdf.copy()  # deepcopy
    districts_on_date = sorted(list(set(data_on_date.region.tolist())))
    name_to_namecount_map = {
        d: d + " Taxis: {:.0f}".format(data_on_date.loc[data_on_date.region == d, 'taxi_count'].values[0]) for d in
        districts_on_date}
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
        fields=["name"],  # , "description"],
        aliases=['District']  # , 'Taxi Count']
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
            )
        ]
    ))


# STREAMLIT CODE BELOW #

# LAYING OUT THE TOP SECTION OF THE APP
# title_container = st.container()
# with title_container:
st.title("Cities in Motion")
# st.subheader(
# """
# Tracking how demand for taxis has changed over the years in Singapore.
# """)
st.write(
    """    
    Discover how Covid has changed taxi demand in Singapore. 
    """)

# st.subheader("Summary (Islandwide)")

with st.expander("Search Parameters", expanded=True):
    row21, row22, row23, row24, row25 = st.columns((1, 1, 1, 1, 1))
    with row21:
        # Delta of (Baseline date + hour + for the next time unit - baseline date + hour)
        baseline_date_start = st.date_input("Pre-Covid Date", value=MIN_DATE_TIME, min_value=MIN_DATE_TIME,
                                            max_value=MIN_COVID_DATE_TIME)
    with row22:
        analysis_date_start = st.date_input("Post-Covid Date", value=MIN_COVID_DATE_TIME,
                                            min_value=MIN_COVID_DATE_TIME, max_value=MAX_DATE_TIME)
    with row23:
        hour_of_day = st.number_input("Time of Day (0-23 hrs)", value=20, min_value=0, max_value=23)
    with row24:
        time_period = st.number_input("For the next", value=10, min_value=1)
    with row25:
        # frequency_list = ("Hours", "Days", "Weeks", "Months", "Years")
        frequency_list = ["Hours", "Days", "Weeks"]
        time_frequency = st.selectbox("Time Unit", frequency_list, index=frequency_list.index("Days"))

# FILTERING DATA BY INPUTS
baseline_data, analysis_data = filter_data(full_data, baseline_date_start, analysis_date_start, hour_of_day,
                                           time_period, time_frequency)

if np.isnan(baseline_data.taxi_count.max()):
    max_count = analysis_data.taxi_count.max()
elif np.isnan(analysis_data.taxi_count.max()):
    max_count = baseline_data.taxi_count.max()
else:
    max_count = max(baseline_data.taxi_count.max(), analysis_data.taxi_count.max())
# st.write(baseline_data.taxi_count.max())
# st.write(analysis_data.taxi_count.max())

row41, row42 = st.columns((1,1))
with row41:
    baseline_from = date_to_datetime(baseline_date_start) + timedelta(hours=int(hour_of_day))
    if (baseline_from >= MIN_DATE_TIME) and (baseline_from <= MIN_COVID_DATE_TIME):
        _date = datetime.strftime(baseline_date_start, "%Y-%m-%d")
        st.markdown(f"##### Pre-Covid: Taxi Demand on {_date}")
        create_folium_choropleth(baseline_data, COUNTRY_GEO, country_gdf, max_count)
    else:
        # invalid input
        st.write("Pre-Covid start date must be between 2016-09-16 13:00 and 2020-04-01 00:00")
with row42:
    analysis_from = date_to_datetime(analysis_date_start) + timedelta(hours=int(hour_of_day))
    if (analysis_from >= MIN_COVID_DATE_TIME) and (analysis_from <= MAX_DATE_TIME):
        _analysis_date = datetime.strftime(analysis_date_start, "%Y-%m-%d")
        st.markdown(f'##### Post-Covid: Taxi Demand on {_analysis_date}')
        create_folium_choropleth(analysis_data, COUNTRY_GEO, country_gdf, max_count)
    else:
        # invalid input
        st.write("Pre-Covid start date must be between 2020-04-01 00:00 and 2021-10-01 00:00")

combined_data = pd.merge(baseline_data, analysis_data, on=['region'], how='outer').rename(
    columns={'region': 'District', 'taxi_count_x': 'Pre-Covid', 'taxi_count_y': 'Post Covid'})
combined_data["Delta"] = abs(combined_data["Post Covid"] - combined_data["Pre-Covid"])
combined_data = combined_data.sort_values(by=['Delta'], ascending=False)
# country_gdf
# combined_data = pd.merge(combined_data, country_gdf[["name", "lat", "long"]], left_on=['District'], right_on=['name'], how='outer').drop(["name"], axis=1)

combined_data_head = combined_data.head(15)
combined_data_tail = combined_data.tail(15)

melted_combined_data_head = combined_data_head.melt(id_vars=['District'], value_vars=['Pre-Covid', 'Post Covid'], var_name='Period', value_name='Taxi Count')
melted_combined_data_tail = combined_data_tail.melt(id_vars=['District'], value_vars=['Pre-Covid', 'Post Covid'], var_name='Period', value_name='Taxi Count')

summary_graph_plotly_head = px.bar(melted_combined_data_head, x='District', y='Taxi Count', color='Period', barmode='group', width=400, height=400, title="Top 15 Districts")
summary_graph_plotly_tail = px.bar(melted_combined_data_tail, x='District', y='Taxi Count', color='Period', barmode='group', width=400, height=400, title="Bottom 15 Districts")

st.markdown(f'##### District-wise Change')
row51, row52 = st.columns((1,1))
with row51:    
    st.plotly_chart(summary_graph_plotly_head, use_container_width=True)
with row52:
    st.plotly_chart(summary_graph_plotly_tail, use_container_width=True)

row61, row62 = st.columns((1, 1))
# with row61:
#----------------------------ANIMATED GRAPH----------------------------
all_districts_data = taxigraph(full_data, "All", hour_of_day, baseline_date_start, analysis_date_start)
all_districts_data["date"] = all_districts_data["filename"].apply(lambda x: pd.to_datetime(x))
all_districts_data = all_districts_data.drop(columns=["rolling_average"])
# all_districts_data["date_str"] = all_districts_data["filename"].apply(lambda x:datetime.strftime(x, "%Y-%m-%d"))
all_districts_data = all_districts_data.groupby([all_districts_data.region.rename("District"),\
    all_districts_data.date.dt.year.rename("year"), all_districts_data.date.dt.month.rename("month")]).agg({'taxi_count':"sum"}).reset_index()
all_districts_data["Date"] = all_districts_data["year"].astype(str) + "-" + all_districts_data["month"].astype(str)
all_districts_data = all_districts_data.drop(columns=["year", "month"])
max_taxi_count = all_districts_data.taxi_count.max()


fig3 = px.bar(all_districts_data, x='District', y='taxi_count', color='District', animation_frame="Date",\
    animation_group="District", \
        hover_name='District', range_y=[0, max_taxi_count], range_x=[0,30], title=f"Top 30 Districts By Available Taxis at {hour_of_day} hours (grouped by month)")\
            .update_xaxes(categoryorder="total descending")
st.plotly_chart(fig3, use_container_width=True)
#----------------------------

st.markdown("***")
st.subheader("Change in Taxi Demand over Time")
st.write('Compare districts to see how taxi demand has changed over time')

row61, row62 = st.columns((1,1))
with row61:
    selected_district_1 = st.selectbox("Select District 1:", list(combined_data.District.unique()))

    district_1_data = taxigraph(full_data, selected_district_1, hour_of_day, baseline_date_start, analysis_date_start)
    # district_1_data["date"] = district_1_data["filename"].apply(lambda x:datetime.strftime(x, "%Y-%m-%d"))
    # district_1_data
    fig1 = px.line(district_1_data, x='date', y=['taxi_count', 'rolling_average'],
        # animation_group="taxi_count", animation_frame="date",\
        title=f'Taxi Data for {selected_district_1} at {hour_of_day} hours')
    st.plotly_chart(fig1, use_container_width=True)


with row62:
    selected_district_2 = st.selectbox("Select District 2:", list(combined_data.District.unique()))
    district_2_data = taxigraph(full_data, selected_district_2, hour_of_day, baseline_date_start, analysis_date_start)
    fig2 = px.line(district_2_data, x='filename', y=['taxi_count', 'rolling_average'], title=f'Taxi Data for {selected_district_2} at {hour_of_day} hours')
    st.plotly_chart(fig2, use_container_width=True)

