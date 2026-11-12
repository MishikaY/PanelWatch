import pandas as pd

gen = pd.read_csv("data/Plant_1_Generation_Data.csv")
wea = pd.read_csv("data/Plant_1_Weather_Sensor_Data.csv")

gen["DATE_TIME"] = pd.to_datetime(gen["DATE_TIME"], dayfirst=True)
wea["DATE_TIME"] = pd.to_datetime(wea["DATE_TIME"])

# average AC power per inverter at each 15-minute timestamp (kW)
p = gen.groupby("DATE_TIME")["AC_POWER"].mean().reset_index()
df = p.merge(wea[["DATE_TIME", "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION"]],
             on="DATE_TIME")
df.columns = ["time", "power", "ambient_temp", "module_temp", "irradiation"]

df["date"] = df["time"].dt.date.astype(str)
df["hour"] = df["time"].dt.hour + df["time"].dt.minute / 60

# keep daytime only, and days with enough readings
df = df[(df["irradiation"] > 0.1) & (df["power"] >= 0)]
counts = df.groupby("date")["power"].transform("count")
df = df[counts >= 30].reset_index(drop=True)

df.to_csv("data/clean.csv", index=False)
print("Rows:", len(df), "| Days:", df["date"].nunique())
print(df.describe().round(2).T[["min", "mean", "max"]])