# NLB Seat-Booking Automation

Personal Python project that books library seats on the National Library Board (NLB) website with Playwright and sends progress updates via Telegram. Not affiliated with NLB.

## Tech
Python, Playwright, Telegram Bot API, GitHub Actions


## Features:
- Book for today or tomorrow, with a configurable start time (9:00 AM–7:00 PM) and duration (1–4 hours)
- Seat fallbacks: preferred seat → backup seat → any available seat
- Waits until 12:00 PM Singapore time (UTC+8) when booking tomorrow, when slots open
- Verifies the "Booking successful!" message before reporting success
- Timestamped Telegram updates (startup, login, page load, booking confirmation)

## Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```
Copy `.env.example` to `.env` and fill in your NLB credentials and Telegram bot settings. Never commit .env.

## Run
```powershell
python main.py
```
Runs headed by default; set HEADLESS=1 for headless. Running the script submits a real booking if a suitable slot is available.

## Configuration

Copy `settings.example.json` to `settings.json` and edit it:

| Setting | Example | Purpose |
| --- | --- | --- |
| `BOOK_FOR` | `"tomorrow"` | Choose `"today"` or `"tomorrow"` |
| `SEAT_OPTION_1` | `9` | Preferred seat; the selector adds `S` |
| `SEAT_OPTION_2` | `5` | Backup seat |
| `TIME_OPTION` | `"1:00 pm"` | Start time matching the website label |
| `DURATION_OPTION` | `"4:00"` | Duration matching the website label |
| `BOOKING_URL` | NLB seat-booking URL | Library location and booking page |

Bookings set for 'today' skip the noon wait, but the chosen time must still be available.

## Library
The script targets HarbourFront Library (HBPL) Seats in the Upper Tier:
```python
BOOKING_URL = "https://www.nlb.gov.sg/seatbooking/?loc=NLB.HBPL.3.ReadingLounge1Upper.{SEAT_OPTION_1}"
```
To use another library, find its location code and update the URL. You could also build your own library selector, but that isn't needed for now.

## Booking Flow
1. Opens Chromium, logs in to NLB.
2. If booking tomorrow before noon, wait until 12:00 PM SGT.
3. book_seat() loads the booking page (page.goto())
4. Selects date, time and duration; picks a seat by preference order.
5. Submits, verifies the success message, sends the Telegram notification, closes the browser.

## GitHub Actions (currently not working)
NLB returns HTTP 403 to GitHub Actions runners, so scheduled runs fail. The intended setup is a workflow at `.github/workflows/nlb-booking.yml` that installs dependencies and runs `main.py`, with credentials stored as repository secrets and a schedule of `55 3 * * *` (11:55 AM SGT) to allow for setup before noon. GitHub schedules are often delayed though, so timing is not guaranteed.

## Notes
- Timestamps are recorded and sent after booking attempt, for no network delays.
- Currently, when "Any available seat" has been booked, the notification displays 'randomly allocated seat'. The same wording is also recorded in booking_log.csv.

## Planned Extensions
-[ ] Send successful booking screenshot to Telegram
-[ ] Set up cloud VM so it runs without manual triggers
-[ ] Implement Telegram commands like `/book_now` or `/skip_tomorrow`(need an always-on handler that verifies the sender):
