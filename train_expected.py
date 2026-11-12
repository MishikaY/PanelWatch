import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import mean_absolute_error, r2_score

df = pd.read_csv("data/clean.csv")
FEAT = ["irradiation", "module_temp", "ambient_temp", "hour"]

def make_model():
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=3,
                                 n_jobs=-1, random_state=1)

# Predict every day using a model that never saw that day (honest results)
exp = cross_val_predict(make_model(), df[FEAT], df["power"],
                        groups=df["date"], cv=GroupKFold(n_splits=5))
df["expected"] = exp

print("== Model 1: expected power (tested on unseen days) ==")
print("MAE (kW):", round(mean_absolute_error(df["power"], exp), 2),
      "| R2:", round(r2_score(df["power"], exp), 4))

# Daily totals and loss
daily = df.groupby("date").agg(actual=("power", "sum"),
                               expected=("expected", "sum")).reset_index()
daily["ratio"] = daily["actual"] / daily["expected"]
median_ratio = float(daily["ratio"].median())
daily["clean_loss"] = 1 - daily["ratio"] / median_ratio
daily.to_csv("data/daily_baseline.csv", index=False)

print("\n== Daily loss on real data (no dust) ==")
print("Average:", round(daily["clean_loss"].mean() * 100, 2), "%")
print("Normal day-to-day wobble (std):", round(daily["clean_loss"].std() * 100, 2), "%")

# Final model trained on all days
final = make_model().fit(df[FEAT], df["power"])
joblib.dump(final, "models/expected_power.pkl")
json.dump({"median_ratio": median_ratio, "features": FEAT},
          open("models/baseline.json", "w"))
print("\nSaved models/expected_power.pkl and models/baseline.json")