from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from api_client import QuotexAPIClient
from scanner import MarketScanner


app = FastAPI(
    title="Trading Signal Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


api_client = QuotexAPIClient()

scanner = MarketScanner(
    api_client=api_client,
    future_score=55,
    monitor_score=65,
    confirmed_score=75,
    signal_ttl_seconds=180,
    max_future_signals=50,
    rescan_interval=10,
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Trading Signal Backend"
    }


@app.get("/api/status")
async def status():
    return {
        "connected": await api_client.check_connection(),
        "scanner_running": scanner.running,
        "live_enabled": scanner.live_enabled,
        "otc_enabled": scanner.otc_enabled,
    }


@app.post("/api/connect")
async def connect(ssid: Optional[str] = None):

    if ssid:
        api_client.ssid = ssid

    try:
        result = await api_client.connect()

        return {
            "success": result,
            "message": "API connected"
        }

    except Exception as exc:

        return {
            "success": False,
            "message": str(exc)
        }


@app.post("/api/scanner/start")
async def start_scanner():

    if not scanner.running:

        import asyncio

        asyncio.create_task(
            scanner.run()
        )

    return {
        "success": True,
        "scanner": "started"
    }


@app.post("/api/scanner/stop")
async def stop_scanner():

    scanner.stop()

    return {
        "success": True,
        "scanner": "stopped"
    }


@app.post("/api/market/live")
async def set_live(enabled: bool = True):

    scanner.set_live_enabled(enabled)

    return {
        "live_enabled":
            scanner.live_enabled
    }


@app.post("/api/market/otc")
async def set_otc(enabled: bool = True):

    scanner.set_otc_enabled(enabled)

    return {
        "otc_enabled":
            scanner.otc_enabled
    }


@app.get("/api/signals")
async def signals():

    return scanner.dashboard_data()


@app.get("/api/signals/future")
async def future_signals():

    return {
        "signals": [
            signal.to_dict()
            for signal
            in scanner.get_future_list()
        ]
    }


@app.get("/api/signals/confirmed")
async def confirmed_signals():

    return {
        "signals": [
            signal.to_dict()
            for signal
            in scanner.get_confirmed()
        ]
    }


@app.get("/api/signals/live")
async def live_signals():

    return {
        "signals": [
            signal.to_dict()
            for signal
            in scanner.get_market_list(
                "LIVE"
            )
        ]
    }


@app.get("/api/signals/otc")
async def otc_signals():

    return {
        "signals": [
            signal.to_dict()
            for signal in scanner.get_market_list(
                "OTC"
            )
        ]
    }


@app.get("/api/statistics")
async def statistics():

    return scanner.statistics()


@app.post("/api/result")
async def update_result(
    pair: str,
    market: str,
    result: str,
):

    success = scanner.update_result(
        pair=pair,
        market=market,
        result=result,
    )

    return {
        "success": success,
        "pair": pair,
        "market": market,
        "result": result.upper(),
    }
