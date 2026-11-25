#!/usr/bin/env python3
"""Daily 'what to wear' push notification based on Buienradar data.

Weather data: Buienradar (https://www.buienradar.nl) public JSON feed.
Notifications: ntfy (https://ntfy.sh) -> free iPhone app, no account needed.

Usage:
    python outfit.py                     # live Buienradar data, send push
    python outfit.py --dry-run           # live data, only print
    python outfit.py --test severe       # use test_data/severe.json, send push
    python outfit.py --test good --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEED_URL = "https://data.buienradar.nl/2.0/feed/json"
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")


# --------------------------------------------------------------------------- data
def load_feed(test: str | None) -> dict:
    if test:
        return json.loads((ROOT / "test_data" / f"{test}.json").read_text(encoding="utf-8"))
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "weather-outfit/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def extract_today(feed: dict, station_name: str, today: date | None = None) -> dict:
    """Pull the numbers we need out of the Buienradar feed."""
    days = feed["forecast"]["fivedayforecast"]
    if today is not None:
        match = [d for d in days if d["day"].startswith(today.isoformat())]
        day = match[0] if match else days[0]
    else:
        day = days[0]

    stations = feed["actual"]["stationmeasurements"]
    station = next((s for s in stations if s.get("stationname") == station_name), stations[0])

    report = feed["forecast"].get("weatherreport", {})
    return {
        "station": station.get("stationname", "?"),
        "min_temp": float(day.get("mintemperatureMin", day.get("mintemperature", 0))),
        "max_temp": float(day.get("maxtemperatureMax", day.get("maxtemperature", 0))),
        "rain_chance": int(day.get("rainChance", 0) or 0),
        "rain_mm": float(day.get("mmRainMax", 0) or 0),
        "sun_chance": int(day.get("sunChance", 0) or 0),
        "wind_bft": int(day.get("wind", 0) or 0),
        "gusts_ms": float(station.get("windgusts", 0) or 0),
        "feel_now": station.get("feeltemperature"),
        "description": day.get("weatherdescription", ""),
        "report_title": report.get("title", ""),
        "report_summary": report.get("summary", ""),
    }


# --------------------------------------------------------------------------- logic
def classify(w: dict, cfg: dict) -> tuple[str, list[str]]:
    """Return ('GOOD' | 'BAD' | 'SEVERE', reasons)."""
    s, b = cfg["severe"], cfg["bad"]
    text = f"{w['description']} {w['report_title']} {w['report_summary']}".lower()

    reasons = []
    if w["wind_bft"] >= s["wind_bft_at_least"]:
        reasons.append(f"storm-force wind ({w['wind_bft']} Bft)")
    if w["gusts_ms"] >= s["gusts_ms_at_least"]:
        reasons.append(f"strong gusts ({w['gusts_ms'] * 3.6:.0f} km/h)")
    if w["min_temp"] <= s["min_temp_at_most"]:
        reasons.append(f"hard frost ({w['min_temp']:.0f}°C)")
    if w["max_temp"] >= s["max_temp_at_least"]:
        reasons.append(f"heat ({w['max_temp']:.0f}°C)")
    if w["rain_mm"] >= s["rain_mm_at_least"]:
        reasons.append(f"heavy rain ({w['rain_mm']:.0f} mm)")
    reasons += [f"warning: '{k}'" for k in s["keywords"] if k in text]
    if reasons:
        return "SEVERE", reasons

    if w["rain_chance"] >= b["rain_chance_at_least"]:
        reasons.append(f"{w['rain_chance']}% chance of rain")
    if w["rain_mm"] >= b["rain_mm_at_least"]:
        reasons.append(f"{w['rain_mm']:.0f} mm rain")
    if w["wind_bft"] >= b["wind_bft_at_least"]:
        reasons.append(f"windy ({w['wind_bft']} Bft)")
    if w["max_temp"] <= b["max_temp_at_most"]:
        reasons.append(f"cold (max {w['max_temp']:.0f}°C)")
    if w["max_temp"] >= b["max_temp_at_least"]:
        reasons.append(f"hot (max {w['max_temp']:.0f}°C)")
    if reasons:
        return "BAD", reasons
    return "GOOD", ["pleasant day"]


def feels_like(w: dict) -> float:
    """Rough 'feels like' daytime temperature: average of min/max, minus wind chill."""
    avg = (w["min_temp"] + w["max_temp"]) / 2
    chill = max(0, w["wind_bft"] - 2) * 1.0 if avg < 15 else 0
    return avg - chill


def outfit(w: dict) -> list[str]:
    t = feels_like(w)
    items: list[str]
    if t < 0:
        items = ["Thermal base layer", "Warm sweater", "Winter coat", "Hat, scarf & gloves", "Warm boots"]
    elif t < 6:
        items = ["Long sleeves + sweater", "Winter coat", "Scarf & gloves", "Closed shoes"]
    elif t < 11:
        items = ["Long sleeves + hoodie/sweater", "Warm jacket", "Jeans or chinos"]
    elif t < 16:
        items = ["Long-sleeve shirt", "Light jacket or cardigan", "Jeans or chinos"]
    elif t < 21:
        items = ["T-shirt or light shirt", "Thin layer for the evening", "Light trousers"]
    elif t < 26:
        items = ["T-shirt", "Shorts or light trousers", "Sneakers"]
    else:
        items = ["Light, breathable clothes", "Shorts", "Sunglasses & sunscreen", "Drink plenty of water"]

    if w["rain_chance"] >= 40 or w["rain_mm"] >= 1:
        items.append("Waterproof jacket" if w["wind_bft"] >= 5 else "Umbrella / rain jacket")
        items.append("Waterproof shoes")
    if w["wind_bft"] >= 5:
        items.append("Windproof outer layer (skip the umbrella)" if w["wind_bft"] >= 6 else "Windproof outer layer")
    if w["sun_chance"] >= 60 and w["max_temp"] >= 18:
        items.append("Sunglasses & sunscreen")
    if w["min_temp"] <= 0:
        items.append("Shoes with grip (possible ice)")
    return list(dict.fromkeys(items))  # dedupe, keep order


def build_message(w: dict, level: str, reasons: list[str]) -> dict:
    icon = {"GOOD": "☀️", "BAD": "🌧️", "SEVERE": "⚠️"}[level]
    title = f"{icon} {level} weather today · {w['min_temp']:.0f}–{w['max_temp']:.0f}°C"
    lines = [
        f"{w['description']}",
        f"Rain {w['rain_chance']}% ({w['rain_mm']:.1f} mm) · Wind {w['wind_bft']} Bft · Sun {w['sun_chance']}%",
    ]
    if level != "GOOD":
        lines.append("Why: " + ", ".join(reasons))
    lines.append("")
    lines.append("👕 Wear today:")
    lines += [f"• {i}" for i in outfit(w)]
    if level == "SEVERE":
        lines += ["", "⚠️ Check buienradar.nl / KNMI warnings before going out."]
    return {
        "title": title,
        "message": "\n".join(lines),
        "priority": {"GOOD": 3, "BAD": 4, "SEVERE": 5}[level],
        "tags": {"GOOD": ["sunny"], "BAD": ["umbrella"], "SEVERE": ["warning"]}[level],
        "click": "https://www.buienradar.nl",
    }


# --------------------------------------------------------------------------- send
def send_ntfy(topic: str, msg: dict) -> None:
    body = json.dumps({"topic": topic, **msg}).encode("utf-8")
    req = urllib.request.Request(
        NTFY_SERVER, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "weather-outfit/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"ntfy returned HTTP {resp.status}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--test", choices=["good", "bad", "severe"], help="use bundled test data instead of live Buienradar")
    p.add_argument("--dry-run", action="store_true", help="print the notification, don't send it")
    args = p.parse_args(argv)

    cfg = load_config()
    feed = load_feed(args.test)
    w = extract_today(feed, os.environ.get("BUIENRADAR_STATION", cfg["station"]),
                      None if args.test else date.today())
    level, reasons = classify(w, cfg)
    msg = build_message(w, level, reasons)
    if args.test:
        msg["title"] = "[TEST] " + msg["title"]

    print(msg["title"])
    print(msg["message"])

    if args.dry_run:
        return 0
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("\nERROR: set NTFY_TOPIC (your ntfy topic name) to send the push.", file=sys.stderr)
        return 1
    send_ntfy(topic, msg)
    print(f"\nSent to ntfy topic '{topic[:3]}…'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
