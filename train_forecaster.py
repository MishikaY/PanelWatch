import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from common import FEATURES, make_features

daily = pd.read_csv("data/daily_baseline.csv")
noise_pool = daily["clean_loss"].values      # real day-to-day wobble
rng = np.random.RandomState(0)

DAYS, N_SCEN = 70, 500
rows, targets, scen = [], [], []

for sc in range(N_SCEN):
    pm_mean = rng.uniform(20, 150)           # how dusty this location is (PM10)
    base_rate = rng.uniform(0.0005, 0.002)   # baseline dirt rate per day
    soil, rain, pm = np.zeros(DAYS), np.zeros(DAYS), np.zeros(DAYS)
    s = 0.0
    for d in range(DAYS):
        pm[d] = max(5, pm_mean * rng.uniform(0.7, 1.3))
        rain[d] = rng.exponential(8) if rng.rand() < 0.08 else 0.0
        s += base_rate + 0.00005 * pm[d]     # dust builds up gradually
        if rain[d] >= 5:   s *= 0.3          # heavy rain washes most dust off
        elif rain[d] >= 2: s *= 0.7          # light rain washes some off
        s = min(s, 0.40)
        soil[d] = s
    observed = soil + rng.choice(noise_pool, DAYS)   # true loss + real-world noise

    for t in range(6, DAYS - 7):
        rows.append(make_features(observed[t - 6:t + 1],
                                  pm[t - 2:t + 1].mean(),
                                  rain[t + 1:t + 4].sum(),
                                  rain[t + 1:t + 8].sum()))
        targets.append([soil[t], soil[t + 3], soil[t + 7]])
        scen.append(sc)

X = pd.DataFrame(rows, columns=FEATURES)
Y = np.array(targets)
scen = np.array(scen)
tr, te = scen < int(N_SCEN * 0.8), scen >= int(N_SCEN * 0.8)

model = RandomForestRegressor(n_estimators=100, min_samples_leaf=40,
                                 n_jobs=-1, random_state=1)
model.fit(X[tr], Y[tr])
pred = model.predict(X[te])

print("== Model 2: loss forecast (tested on unseen scenarios) ==")
names = ["loss now", "loss in 3 days", "loss in 7 days"]
naive = X.loc[te, ["l4", "l5", "l6"]].mean(axis=1).values   # 'same as last 3 days'
for i, n in enumerate(names):
    print(f"{n:15s} | AI error: {mean_absolute_error(Y[te][:, i], pred[:, i])*100:.2f} pts"
          f" | naive error: {mean_absolute_error(Y[te][:, i], naive)*100:.2f} pts")

joblib.dump(model, "models/forecaster.pkl")
print("\nSaved models/forecaster.pkl")