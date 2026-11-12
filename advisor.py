import numpy as np

def severity_of(loss):
    if loss < 0.03: return "NORMAL"
    if loss < 0.08: return "LOW"
    if loss < 0.15: return "MEDIUM"
    return "HIGH"

def advise(last7, now, f3, f7, rain_next3, daily_kwh=100.0, tariff=6.0, clean_cost=500.0):
    """
    last7: last 7 daily losses (fractions) | now/f3/f7: loss now, in 3 days, in 7 days
    daily_kwh: energy the panel/plant makes on a clean day | tariff: money per kWh
    clean_cost: cost of one cleaning
    """
    sev = severity_of(now)
    last7 = np.asarray(last7, float)

    # Sudden drop = probably NOT dust
    jump = last7[-1] - last7[:-1].mean()
    if jump > 0.06:
        return dict(severity="HIGH", type="SUDDEN DROP", loss_pct=now * 100,
                    money_per_day=now * daily_kwh * tariff,
                    advice="Power fell suddenly. This does not look like dust. "
                           "Inspect for shading, a faulty inverter or wiring problems.")

    money_day = now * daily_kwh * tariff
    money_week = (now + f7) / 2 * 7 * daily_kwh * tariff

    if sev == "NORMAL":
        advice = "Panels are performing normally. No action needed."
    elif rain_next3 >= 5 and sev in ("LOW", "MEDIUM"):
        advice = (f"{sev.title()} dust loss, but heavy rain ({rain_next3:.0f} mm) is expected "
                  "within 3 days. Rain should wash the panels. Wait and re-check afterwards.")
    elif sev == "LOW":
        advice = ("Dust is building up slowly. Add cleaning to the next routine visit."
                  + (f" Forecast: {severity_of(f7).lower()} level within 7 days." if severity_of(f7) != sev else ""))
    elif sev == "MEDIUM":
        advice = "Schedule panel cleaning within the next 3 days."
        if money_week > clean_cost:
            advice += f" Waiting a week costs about {money_week:.0f}, more than a cleaning ({clean_cost:.0f})."
    else:
        advice = ("Clean the panels immediately. If power does not recover after "
                  "cleaning, inspect for other faults.")

    return dict(severity=sev, type="GRADUAL SOILING" if now >= 0.03 else "NONE",
                loss_pct=now * 100, forecast_3d_pct=f3 * 100, forecast_7d_pct=f7 * 100,
                money_per_day=money_day, money_next_7d=money_week, advice=advice)

if __name__ == "__main__":
    # demo: dust creeping up over a week, no rain coming
    print(advise([0.02, 0.025, 0.03, 0.04, 0.045, 0.05, 0.06],
                 now=0.06, f3=0.085, f7=0.12, rain_next3=0))