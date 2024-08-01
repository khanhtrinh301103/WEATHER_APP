import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry

app = Flask(__name__)

@app.route('/')
def index():
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # API request
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 10.823,
        "longitude": 106.6296,
        "current_weather": "true",
        "daily": ["temperature_2m_max", "temperature_2m_min", "sunshine_duration", "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant"],
        "timezone": "Asia/Bangkok",
        "past_days": 61,
        "forecast_days": 1
    }
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Process data for daily values
        daily = response.Daily()
        if daily is not None:
            daily_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                    end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(days=1),
                    inclusive="left"
                ),
                "temperature_2m_max": daily.Variables(0).ValuesAsNumpy(),
                "temperature_2m_min": daily.Variables(1).ValuesAsNumpy(),
                "sunshine_duration": daily.Variables(2).ValuesAsNumpy(),
                "precipitation_sum": daily.Variables(3).ValuesAsNumpy(),
                "precipitation_probability_max": daily.Variables(4).ValuesAsNumpy(),
                "wind_speed_10m_max": daily.Variables(5).ValuesAsNumpy(),
                "wind_gusts_10m_max": daily.Variables(6).ValuesAsNumpy(),
                "wind_direction_10m_dominant": daily.Variables(7).ValuesAsNumpy(),
            }
            daily_df = pd.DataFrame(data=daily_data)

            # Create daily temperature plot
            fig, ax = plt.subplots()
            ax.plot(daily_df['date'], daily_df['temperature_2m_max'], label='Max Temperature')
            ax.plot(daily_df['date'], daily_df['temperature_2m_min'], label='Min Temperature')
            ax.set_title('Daily Temperature')
            ax.set_xlabel('Date')
            ax.set_ylabel('Temperature (°C)')
            ax.legend()

            # Save plot to a PNG image in memory
            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode('utf8')

            return render_template('index.html', plot_url=plot_url)
        else:
            return "No daily data available."
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == '__main__':
    app.run(debug=True)
