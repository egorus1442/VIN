from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import uvicorn
import requests
from bs4 import BeautifulSoup

class VinRequest(BaseModel):
    vin: str

app = FastAPI(title="VIN Decoder API")

def get_vin_info(vin: str,
                 solver_url: str = "http://flaresolverr:8191/v1",
                 max_timeout: int = 60000) -> Dict:
    payload = {
        "cmd": "request.get",
        "url": f"https://www.vindecoderz.com/EN/check-lookup/{vin}",
        "maxTimeout": max_timeout,
        "waitForSelector": "table.table-striped"
    }
    resp = requests.post(solver_url, json=payload)
    resp.raise_for_status()
    html = resp.json()["solution"]["response"]

    soup = BeautifulSoup(html, "html.parser")
    info = {}

    # таблица основных данных
    t1 = soup.find("table", class_="table-hover")
    if not t1:
        raise HTTPException(502, "Failed to parse main table")
    for tr in t1.find_all("tr"):
        tds = tr.find_all("td")
        key = tds[0].get_text(strip=True).rstrip(":")
        if key == "WMI/VDS/VIS":
            for a in tds[1].find_all("a"):
                sub = a.get("title", "").split(" - ", 1)[0]
                info[sub] = a.get_text(strip=True)
        elif key == "Mileage":
            info["MileageReportURL"] = tds[1].find("a")["href"]
        else:
            info[key] = tds[1].get_text(strip=True)

    # таблица Build Sheet (если есть)
    t2 = soup.find("table", class_="table-striped")
    if t2:
        for tr in t2.find_all("tr"):
            cols = tr.find_all("td")
            info[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

    return info

@app.post("/vin", summary="Получить данные по VIN")
def decode_vin(req: VinRequest):
    try:
        data = get_vin_info(req.vin)
        return {"status": "ok", "vin": req.vin, "data": data}
    except requests.HTTPError as e:
        raise HTTPException(502, f"FlareSolverr error: {e}")
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
