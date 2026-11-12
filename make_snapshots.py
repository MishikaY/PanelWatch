import os
import pandas as pd
from pipeline import _fetch_weather

CITIES = {"New Delhi": (28.61, 77.21), "Jaipur": (26.91, 75.79),
          "Mumbai": (19.08, 72.88), "Bengaluru": (12.97, 77.59),
          "Chennai": (13.08, 80.27)}

os.makedirs("data/snapshots", exist_ok=True)
for name, (lat, lon) in CITIES.items():
    h = _fetch_weather(lat, lon).drop(columns=["date"])
    h["saved_on"] = str(pd.Timestamp.now().date())
    h.to_csv(f"data/snapshots/{round(lat, 2)}_{round(lon, 2)}.csv", index=False)
    print("saved", name)