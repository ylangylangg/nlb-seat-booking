print("RUNNING FILE:",__file__, flush=True)

import os 
import re
import requests
from getpass import getpass
from playwright.sync_api import Page, TimeoutError as PWTimeout, sync_playwright, expect
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import time
import csv
import json
from pathlib import Path

load_dotenv(Path(__file__).with_name(".env"))

SETTINGS_PATH = Path(__file__).with_name("settings.json")

with SETTINGS_PATH.open(encoding="utf-8") as file:
    settings = json.load(file)

BOOK_FOR = settings["BOOK_FOR"]
BOOKING_TIME = settings["BOOKING_TIME"]
BOOKING_DURATION = settings["BOOKING_DURATION"]
SEAT_OPTION_1 = settings["SEAT_OPTION_1"]
SEAT_OPTION_2 = settings["SEAT_OPTION_2"]

LOGIN_URL = "https://www.nlb.gov.sg/seatbooking/login/options"
BOOKING_URL = "https://www.nlb.gov.sg/seatbooking/?loc=NLB.HBPL.3.ReadingLounge1Upper.{SEAT_OPTION_1}"

USERNAME = os.environ.get("NLB_USERNAME") 
PASSWORD = os.environ.get("NLB_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HEADLESS = os.environ.get("HEADLESS", "0") == "1" # For no visible window, set env: HEADLESS = value == "1"
TIMEOUT_MS = 300_000
SG_TIMEZONE = timezone(timedelta(hours=8))
DATE_TODAY = datetime.now(SG_TIMEZONE).date()
if BOOK_FOR == "today":
    BOOKING_DATE = DATE_TODAY
elif BOOK_FOR == "tmr":
    BOOKING_DATE = DATE_TODAY + timedelta(days=1)
else:
    raise ValueError('BOOK_FOR must be "today" or "tmr"')


def timestamp():
    return datetime.now(SG_TIMEZONE).strftime("%H:%M:%S")

def login(page: Page) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    username_field = page.locator("#username")
    password_field = page.locator("#password")

    username_field.fill(USERNAME, timeout=15_000)
    password_field.fill(PASSWORD)

    page.get_by_role("button", name="CONTINUE", exact=True).click()

    # verify signed in
    expect(page).to_have_url(
        re.compile(r"https://www.nlb.gov.sg/seatbooking/"),
        timeout=15_000
        )


def pick_option(page: Page, label_pattern: str, option_text: str) -> None:
    label_re = re.compile(label_pattern, re.I) # re.I ignores capitalisation

    # note: option_text is the text iw, i.e. "1:00"
    for locator in ( # try two ways to find the dropdown
        page.get_by_label(label_re), 
        page.get_by_role("combobox", name=label_re)):
        if locator.count():
            el = locator.first # choose the first match
            tag = el.evaluate("e => e.tagName.toLowerCase()")
            if tag == "select":
                el.select_option(label=option_text)
                return

            # custom combobox: opens and picks the option
            el.click()
            page.get_by_role(
                "option", # find this element
                name=re.compile(re.escape(option_text), re.I)
                # re.escape(option_text) treats the text literally
                # re.compile(..., re.I) for matching rule, caps ok
                ).first.click()
            return

            # for exact text match, simplifies to:
            # page.get_by_role("option", name=option_text, exact=True).click()

def book_seat(page: Page) -> str:
    page.goto(BOOKING_URL, wait_until="domcontentloaded")

    # date: open calendar
    page.get_by_role("textbox", name="Select date").click()
    if DATE_TODAY.month != BOOKING_DATE.month:
        page.get_by_role(
            "button", name=DATE_TODAY.strftime("%B"), exact=True
        ).click()

        page.get_by_role(
            "cell", name=BOOKING_DATE.strftime("%b"), exact=True
        ).click()

    page.get_by_role("button", name=str(BOOKING_DATE.day), exact=True).click()

    # time
    page.get_by_role("textbox", name="Select time", exact=True).click()
    page.get_by_text(BOOKING_TIME, exact=True).click()

    # duration
    page.get_by_role("textbox", name="Select duration", exact=True).click()
    page.get_by_text(BOOKING_DURATION, exact=True).click()

    print(f"Selected for {BOOKING_DATE.strftime("%d %b")}, {BOOKING_TIME}, {BOOKING_DURATION}")

    # availability
    page.get_by_role(
        "button", name="Check available slots", exact=True
    ).click()

    # in case
    login_to_book = page.get_by_role("button", name="Login to Book", exact=True)

    if login_to_book.is_visible():
        login_to_book.click()

    # book
    page.get_by_role("button", name="Book", exact=True).click()

    # open seat selector
    selection_dialog = page.get_by_role("dialog").filter(has_text="Selection")
    seat_input = selection_dialog.locator("input[readonly]")
    seat_input.click()

    # recorded seat selection:
    if page.get_by_text(f"S{SEAT_OPTION_1}", exact=True).is_visible():
        selected_seat = f"S{SEAT_OPTION_1}"
    elif page.get_by_text(f"S{SEAT_OPTION_2}", exact=True).is_visible():
        selected_seat = f"S{SEAT_OPTION_2}"
    else: 
        selected_seat = "Any available seat"  # fallback

    page.get_by_text(selected_seat, exact=True).click()

    # book
    page.get_by_role("button", name="Confirm", exact=True).click()

    if selected_seat == "Any available seat":
        return "randomly allocated seat"

    return selected_seat

def send_telegram(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=15,
    )

    if not response.json().get("ok"):
        raise RuntimeError("telegram notification failed")

def send_screenshot(page, caption=""):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    screenshot = page.screenshot(full_page=True) # can adjust later

    response = response.post(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data={"chat_id": chat_id, "caption": caption},
        files={"photo": ("booking.png", screenshot, "image/png"),},
        timeout=30
    )

    response.raise_for_status()

    if not response.json().get("ok"):
        raise RuntimeError("telegram screenshot failed")


def wait_until_noon():
    now = datetime.now(SG_TIMEZONE)
    target = now.replace(hour=12, minute=0, second=0, microsecond=5)

    print("waiting until noon SGT...", flush=True)

    while True:
        remaining = (target - datetime.now(SG_TIMEZONE)).total_seconds()

        if remaining <= 0:
            break

        time.sleep(min(remaining, 0.1))

def main() -> None:
    script_started_at = timestamp()
    logged_in_at = None
    booked_at = None
    
    if not USERNAME or not PASSWORD:
        raise ValueError("Set NLB_USERNAME and NLB_PASSWORD first.")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS, # show browser while debugging
            slow_mo=150,
            args=["--window-size=960,1000","--window-position=0,0"]
            )

        context = browser.new_context(no_viewport=True)
        context.grant_permissions([])  # Deny permission requests
        context.set_default_timeout(TIMEOUT_MS)
        page = context.new_page()

        try:
            login(page)
            logged_in_at = timestamp()

            # wait if necessary
            if BOOK_FOR == "tmr" and datetime.now(SG_TIMEZONE).hour < 12:
                wait_until_noon()

            # attempt booking
            selected_seat = book_seat(page)

            # verify success
            expect(
                    page.get_by_text("Booking successful!", exact=True)
                ).to_be_visible(timeout=30_000)

            booked_at = timestamp()

            # track by appending to booking_log.csv after confirmed success
            log_path = Path("booking_log.csv")
            needs_header = not log_path.exists() or log_path.stat().st_size == 0

            with log_path.open("a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)

                if needs_header:
                    writer.writerow(["date", "seat", "time", "duration"])

                writer.writerow([
                    BOOKING_DATE.isoformat(),
                    selected_seat,
                    BOOKING_TIME,
                    BOOKING_DURATION,
                ])

        finally:
            messages = []
        
            if logged_in_at is not None:
                messages.append(f"{logged_in_at} login confirmed")

            if booked_at is not None:
                success_message = (
                    f"{booked_at} ☆ booking success ☆\n"
                    f"Seat: {selected_seat} for {BOOKING_DATE.strftime('%d %b')}"
                )
                messages.append(success_message)

                try:
                    send_screenshot(page, caption=success_message)

                except Exception as error:
                    print(f"screenshot delivery error: {error}")
                    messages.append("\nbooking confirmed, but screenshot delivery failed")

            else:
                messages.append("unable to verify booking")
        
            try:
                send_telegram("\n".join(messages))
            except Exception as notification_error:
                print(
                    "telegram notification failed: "
                    f"{type(notification_error).__name__}"
                )

            # can add a fallback if unsuccessful booking, try again, for middle tier seat S18
        context.close()
        browser.close()

if __name__ == "__main__":
    main()





