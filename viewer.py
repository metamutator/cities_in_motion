import datetime as dt
from datetime import datetime
import folium
import geopandas as gpd
import json
from shapely import wkt
import streamlit as st
from streamlit_folium import folium_static
import pandas as pd
import matplotlib.pyplot as plt


def load_taxi_count():
    # processed_fname = f'gs://dva-sg-team105/processed_summary/processed_taxi_count.all.csv'
    year_dfs = [pd.read_csv(f'data/analysis/processed_taxi_count.{year}.csv', index_col=0) for year in range(2016, 2022)]
    _df = pd.concat(year_dfs, axis=0)        
    
    # processed_fname = 'data/processed/processed_taxi_count.all.csv'
    # _df = pd.read_csv(processed_fname, index_col=0)

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


def load_taxi_locations():
    # fname = f'gs://dva-sg-team105/processed/2021/taxi_region.20211001000000.csv'
    fname = 'data/processed/2021/taxi_region.20211001000000.csv'

    df = pd.read_csv(fname, index_col=0)

    # add geometry
    df['geometry'] = df['geometry'].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(df, crs='epsg:4326')
    return gdf


def load_country_gdf():
    # fname = f'gs://dva-sg-team105/region1.geojson'
    fname = 'data/region1.geojson'

    with open(fname, "rb") as f:
        country_json = json.load(f)
    country_gdf = gpd.GeoDataFrame.from_features(country_json)
    return country_gdf

def create_folium_choropleth(taxi_count_df, country_geo):
    # center on Singapore
    m = folium.Map(location=[1.3572, 103.8207], zoom_start=11)

    folium.Choropleth(
        geo_data=country_geo,
        name="choropleth",
        data=taxi_count_df,
        columns=["region", "taxi_count"],
        key_on="feature.properties.name",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Taxi Count",
    ).add_to(m)

    # call to render Folium map in Streamlit
    folium_static(m)


def run():
    st.header('DVA Team 105')

    taxi_count_df = load_taxi_count()
    # taxi_count_df = taxi_count_df.loc['2021-10-01']
    # st.write(df)

    # gdf = load_taxi_locations()

    country_geo = 'data/region1.geojson'
    country_gdf = load_country_gdf()

    # left_col, right_col = st.columns(2)  # not working

    input_date = st.date_input('Baseline date', value=dt.date(2016, 9, 16), min_value=dt.date(2016, 9, 16), max_value=dt.date(2020, 3, 31))
    _date = datetime.strftime(input_date, "%Y-%m-%d")
    # _date = '2016-09-16'
    st.text(f'Taxi Count at {_date}')
    create_folium_choropleth(taxi_count_df.loc[_date], country_geo)

    input_date = st.date_input('Analysis date', value=dt.date(2020, 4, 1), min_value=dt.date(2020, 4, 1), max_value=dt.date(2021, 10, 1))
    _date = datetime.strftime(input_date, "%Y-%m-%d")
    # _date = '2021-10-01'
    st.text(f'Taxi Count at {_date}')
    create_folium_choropleth(taxi_count_df.loc[_date], country_geo)

    pass


if __name__ == "__main__":
    run()
