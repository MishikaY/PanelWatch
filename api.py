import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pipeline import build_report
from typing import Optional

app = FastAPI(title="Solar Power Loss Monitor")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
DB = "data/monitor.db"


def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created TEXT DEFAULT CURRENT_TIMESTAMP,
        lat REAL, lon REAL, severity TEXT,
        loss_pct REAL, f3 REAL, f7 REAL, advice TEXT)""")
    return con


@app.get("/")
def root():
    return {"status": "ok", "message": "Solar loss monitor is running"}


@app.get("/report")
def report(lat: float = 28.61, lon: float = 77.21, system_kw: float = 100.0,
           tariff: float = 6.0, clean_cost: float = 500.0,
           days_since_clean: int = 14, pm10: Optional[float] = None,
           rain_next3: Optional[float] = None):
    try:
        r = build_report(lat, lon, tariff, clean_cost, system_kw,
                         days_since_clean, pm10, rain_next3)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not build report: {e}")
    a = r["assessment"]
    con = db()
    con.execute("INSERT INTO reports (lat,lon,severity,loss_pct,f3,f7,advice) "
                "VALUES (?,?,?,?,?,?,?)",
                (lat, lon, a["severity"], a["loss_pct"],
                 a["forecast_3d_pct"], a["forecast_7d_pct"], a["advice"]))
    con.commit()
    con.close()
    return r

@app.get("/history")
def history(limit: int = 50):
    con = db()
    rows = con.execute("SELECT created,lat,lon,severity,loss_pct,f3,f7,advice "
                       "FROM reports ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    keys = ["created", "lat", "lon", "severity", "loss_pct", "f3", "f7", "advice"]
    return [dict(zip(keys, r)) for r in rows]