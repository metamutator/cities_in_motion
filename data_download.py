import requests
import json
import numpy as np
import pandas as pd

from tqdm import tqdm
from os.path import exists


def multiproc(n_proc):
    pass


def download_data(start, end, freq='5Min'):
    date_range = pd.date_range(start='2018-01-01', end='2019-10-01', freq='5Min')
    for _dt in tqdm(date_range):
        _dt = str(_dt).replace(' ', 'T')
        dt_int = _dt.replace('-', '').replace('T', '').replace(':', '')
        year = _dt[:4]
        fname = f"data/{year}/{dt_int}.json"
        if exists(fname):
            continue
        
        dt_url = _dt.replace(':', '%3A')
        url = f"https://api.data.gov.sg/v1/transport/taxi-availability?date_time={dt_url}"
        
        try:
            resp = requests.get(url=url)
            data = resp.json()
        except Exception as e:
            print(e)
            continue

        with open(f"data/{year}/{dt_int}.json", "w") as f:
            json.dump(data, f, indent=4)



