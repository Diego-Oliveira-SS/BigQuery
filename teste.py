# Normaliza o JSON do forecast em linhas "tabeláveis" (1 chamada)
import datetime as dt, requests, pandas as pd, os

id = 3456282

API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

def forecast_weather(city_id: int):
    forecast = requests.get(
        "http://api.openweathermap.org/data/2.5/forecast",
        params={
            "id": city_id,
            "appid": "3bbb6be0fbb35ba9bb21cd1bc82aa1c0",
            "units": "metric",
            "lang": "pt_br"
        },
        timeout=15
    ).json()

forecast = forecast_weather(id)
print(forecast)
