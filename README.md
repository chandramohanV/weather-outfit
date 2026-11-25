# Weather Outfit 👕☔

Every morning this app reads today's forecast from [Buienradar](https://www.buienradar.nl) and sends a
push notification to your iPhone. The notification tells you whether the weather is **GOOD**, **BAD** or
**SEVERE** and what to wear.

- **Weather data:** Buienradar's public JSON feed (`https://data.buienradar.nl/2.0/feed/json`). Source: buienradar.nl
- **Push to iPhone:** [ntfy](https://ntfy.sh), a free app with no account needed
- **Runs on:** GitHub Actions (free), every day at 06:30 Amsterdam time in winter (07:30 in summer), so no server is needed

## Example notification

```
⚠️ SEVERE weather today · 4–8°C
Storm met zware windstoten en onweer
Rain 95% (25.0 mm) · Wind 8 Bft · Sun 0%
Why: storm-force wind (8 Bft), strong gusts (97 km/h), heavy rain (25 mm)

👕 Wear today:
• Long sleeves + sweater
• Winter coat
• Waterproof jacket
• Windproof outer layer (skip the umbrella)
```

## Setup (about 5 minutes)

1. **Install ntfy on your iPhone** from the App Store ("ntfy").
2. **Pick a secret topic name** that's hard to guess, e.g. `outfit-chandra-8f3k2q`. Anyone who knows the
   name can read the topic, so treat it like a password.
3. In the ntfy app, tap **+** and **subscribe** to that topic. Allow notifications when iOS asks.
4. In this GitHub repo, open **Settings → Secrets and variables → Actions**:
   - **Secrets** tab: add `NTFY_TOPIC` = your topic name
   - **Variables** tab (optional): add `BUIENRADAR_STATION` = e.g. `Meetstation Rotterdam`
     (default is `Meetstation Schiphol`; see the station list below)

## 🧪 Test the notification on your phone

Go to **Actions → Daily outfit notification → Run workflow**, choose a scenario and press **Run workflow**:

| Scenario | Test data | Expected push |
|---|---|---|
| `good` | 14–22°C, sunny, light wind | ☀️ GOOD, normal priority |
| `bad` | 6–10°C, 80% rain, 5 Bft | 🌧️ BAD, high priority |
| `severe` | Storm 8 Bft, gusts 97 km/h, thunder, code orange | ⚠️ SEVERE, urgent priority |
| `live` | Real Buienradar data right now | depends on the weather |

Test notifications start with `[TEST]`. The test data lives in `test_data/*.json` and uses the same format as
the real Buienradar feed, so you can edit it to try your own cases.

You can also test from your own computer:

```bash
python outfit.py --test severe --dry-run           # print only
NTFY_TOPIC=your-topic python outfit.py --test bad  # send to phone
python outfit.py --dry-run                         # live Buienradar data
python -m unittest discover -s tests -v            # unit tests
```

The app uses only the Python standard library, so there's nothing to install.

## Changing what counts as good, bad or severe

Edit `config.json`:

- **SEVERE** if any of these: wind ≥ 7 Bft, gusts ≥ 20 m/s (72 km/h), min ≤ −5°C, max ≥ 32°C, rain ≥ 15 mm,
  or the forecast text mentions *onweer, storm, ijzel, gladheid, hagel, sneeuw, code oranje/rood*
- **BAD** if any of these: rain chance ≥ 60%, rain ≥ 2 mm, wind ≥ 5 Bft, max ≤ 5°C or ≥ 28°C
- **GOOD** otherwise

The clothing rules are in the `outfit()` function in `outfit.py`. They're based on the day's average
temperature minus wind chill, plus extras for rain, wind, sun and frost.

## Changing the time

Edit the `cron` line in `.github/workflows/daily.yml`. The time is in UTC. Note: GitHub can delay
scheduled runs by a few minutes, and pauses schedules on repos with no activity for 60 days.

## Stations

Arnhem, Berkhout, De Bilt, Den Helder, Eindhoven, Ell, Gilze Rijen, Goes, Groenlo-Hupsel, Groningen, Heino,
Herwijnen, Hoek van Holland, Hoogeveen, Hoorn Terschelling, Horst, Houtribdijk, IJmuiden, Lauwersoog,
Leeuwarden, Lelystad, Lopik-Cabauw, Maastricht, Marknesse, Nieuw Beerta, Rotterdam, Rotterdam Geulhaven,
Schiphol, Stavoren, Texelhors, Twente, Vlieland, Vlissingen, Volkel, Voorschoten, Westdorpe, Wijdenes,
Wijk aan Zee, Woensdrecht. Always use the format `Meetstation <name>`.

Data source: Buienradar (https://www.buienradar.nl)
