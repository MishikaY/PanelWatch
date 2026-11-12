import numpy as np

FEATURES = [f"l{i}" for i in range(7)] + ["mean7", "slope5", "pm10_recent",
                                         "rain_next3", "rain_next7"]

def make_features(last7, pm10_recent, rain_next3, rain_next7):
    """last7 = daily loss fractions, oldest first (7 values)."""
    last7 = np.asarray(last7, float)
    slope = np.polyfit(np.arange(5), last7[-5:], 1)[0]   # trend over the last 5 days
    return [*last7, last7.mean(), slope, pm10_recent, rain_next3, rain_next7]