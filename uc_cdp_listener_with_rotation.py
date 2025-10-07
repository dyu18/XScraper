#!/usr/bin/env python3
"""
Capture X (Twitter) GraphQL responses containing 'SearchTimeline' using
Chrome DevTools (performance logs + CDP) with undetected-chromedriver (UC).

Features:
- Iterates through date windows (e.g., 15 days)
- Handles rate limits by rotating between logged-in profiles
- Detects when no more tweets are available for a given date window
- Saves data in per-user subdirectories
- Persists progress across restarts (resumes where it left off)
- Uses structured logging instead of print statements
"""

import os
import time
import json
import base64
import threading
import datetime
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List
import undetected_chromedriver as uc


# -------------------- Configuration -------------------- #
USERNAMES = ["realDonaldTrump", "elonmusk"]
SINCE_DATE = "2025-10-01"
UNTIL_DATE = "2025-10-07"
DATE_WINDOW_DAYS = 1

SCROLLS = 100
SCROLL_PAUSE = 1.2
OUT_DIR = Path("tweet_responses")
ROTATE_DELAY = 10  # seconds before trying next profile
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

AVAILABLE_DIRECTORIES = [
    "twitter_data_dir_tophaneliomer",
    "twitter_data_dir_verdacokhakim",
]
# ------------------------------------------------------- #

OUT_DIR.mkdir(exist_ok=True)


# -------------------- Logging Setup -------------------- #
def setup_logger():
    logger = logging.getLogger("tweet_crawler")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_DIR / "crawler.log", maxBytes=5_000_000, backupCount=30
    )
    file_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    return logger


logger = setup_logger()


# -------------------- Helpers -------------------- #
def daterange_chunks(start_date: str, end_date: str, days: int):
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    while start < end:
        until = min(start + datetime.timedelta(days=days), end)
        yield (start.isoformat(), until.isoformat())
        start = until


def build_search_url(username: str, since_date: str, until_date: str) -> str:
    import urllib.parse
    q = f"from:{username} since:{since_date} until:{until_date}"
    return "https://x.com/search?q=" + urllib.parse.quote(q, safe="") + "&src=typed_query&f=live"


# -------------------- State Management -------------------- #
def state_file(username: str) -> Path:
    return Path(f"crawl_state_{username}.json")


def save_state(username: str, profile_idx: int, since: str, until: str):
    data = {"last_profile_idx": profile_idx, "last_since": since, "last_until": until}
    with open(state_file(username), "w") as f:
        json.dump(data, f)
    logger.info(f"Progress saved for {username}: profile={profile_idx}, {since}->{until}")


def load_state(username: str):
    path = state_file(username)
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load state for {username}: {e}")
        return None


def clear_state(username: str):
    path = state_file(username)
    if path.exists():
        path.unlink()
        logger.info(f"Cleared saved state for {username}")


# -------------------- Browser / CDP Classes -------------------- #
class UCSession:
    def __init__(self, profile_dir: str):
        self.profile_dir = os.path.abspath(profile_dir)
        self.driver = None

    def __enter__(self):
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        options.set_capability("browserName", "chrome")

        logger.info(f"Starting Chrome with profile: {self.profile_dir}")
        self.driver = uc.Chrome(options=options)
        self.driver.execute_cdp_cmd("Network.enable", {})
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing browser for {self.profile_dir}: {e}")
        logger.info(f"Closed browser for {self.profile_dir}")


class CDPResponseSaver(threading.Thread):
    def __init__(self, driver, out_dir, poll_interval=0.8):
        super().__init__(daemon=True)
        self.driver = driver
        self.out_dir = out_dir
        self.poll_interval = poll_interval
        self.running = False
        self.seen_request_ids = set()
        self.counter = 0
        self.last_response_time = 0
        self.rate_limited = False
        self.no_more_tweets = False

    def run(self):
        self.running = True
        while self.running:
            try:
                for msg in self._get_perf_messages():
                    self._handle_message(msg)
            except Exception as e:
                logger.error(f"CDP listener error: {e}")
            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False

    def _get_perf_messages(self):
        try:
            entries = self.driver.get_log("performance")
        except Exception:
            return []
        msgs = []
        for e in entries:
            try:
                msg = json.loads(e["message"])["message"]
                msgs.append(msg)
            except Exception:
                continue
        return msgs

    def _handle_message(self, msg):
        if msg.get("method") != "Network.responseReceived":
            return
        params = msg.get("params", {})
        response = params.get("response", {})
        request_id = params.get("requestId")
        url = response.get("url", "")

        if "SearchTimeline" not in url or not request_id or request_id in self.seen_request_ids:
            return

        self.seen_request_ids.add(request_id)
        try:
            body_resp = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
            body = body_resp.get("body", "")
            if body_resp.get("base64Encoded", False):
                body_bytes = base64.b64decode(body)
            else:
                body_bytes = body.encode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed to read response body for {url}: {e}")
            return

        text_preview = body_bytes[:1000].decode("utf-8", errors="ignore").lower()
        if "rate limit exceeded" in text_preview:
            logger.warning("Rate limit detected, stopping this profile.")
            self.rate_limited = True
            self.stop()
            return

        try:
            data = json.loads(body_bytes.decode("utf-8", errors="ignore"))
            instructions = (
                data.get("data", {})
                .get("search_by_raw_query", {})
                .get("search_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
            )
            entries = []
            for inst in instructions:
                if inst.get("type") == "TimelineAddEntries":
                    entries.extend(inst.get("entries", []))
            if not entries:
                logger.info("No tweets found for this date window.")
                self.no_more_tweets = True
                self.stop()
                return
        except Exception:
            pass

        filename = f"resp_{int(time.time())}_{self.counter}.json"
        out_path = self.out_dir / filename
        try:
            with open(out_path, "wb") as f:
                f.write(body_bytes)
            logger.info(f"Saved SearchTimeline response: {out_path}")
            self.last_response_time = time.time()
            self.counter += 1
        except Exception as e:
            logger.error(f"Error saving file {out_path}: {e}")


# -------------------- Core Logic -------------------- #
def scroll_and_capture(driver, saver: CDPResponseSaver, username: str, since: str, until: str):
    url = build_search_url(username, since, until)
    logger.info(f"Navigating to {url}")
    driver.get(url)
    time.sleep(2)

    for i in range(SCROLLS):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        if saver.rate_limited:
            return "rate_limited"
        if saver.no_more_tweets:
            return "no_more_tweets"
    return "ok"


def run_with_rotation(directories: List[str], username: str):
    date_chunks = list(daterange_chunks(SINCE_DATE, UNTIL_DATE, DATE_WINDOW_DAYS))
    logger.info(f"Processing {len(date_chunks)} windows for {username} ({DATE_WINDOW_DAYS} days each)")

    state = load_state(username)
    profile_idx = 0
    start_chunk = 0

    if state:
        profile_idx = min(state.get("last_profile_idx", 0), len(directories) - 1)
        last_since = state.get("last_since")
        for i, (s, _) in enumerate(date_chunks):
            if s == last_since:
                start_chunk = i
                break
        logger.info(f"Resuming {username} from profile {directories[profile_idx]}, chunk {start_chunk + 1}")
    else:
        logger.info(f"Starting new crawl for {username}")

    while True:
        profile_dir = directories[profile_idx]
        logger.info(f"Using profile {profile_dir} ({profile_idx + 1}/{len(directories)})")

        with UCSession(profile_dir) as driver:
            for i in range(start_chunk, len(date_chunks)):
                since, until = date_chunks[i]
                sub_out_dir = OUT_DIR / username / f"{since}_{until}"
                sub_out_dir.mkdir(parents=True, exist_ok=True)

                saver = CDPResponseSaver(driver, sub_out_dir)
                saver.start()
                status = scroll_and_capture(driver, saver, username, since, until)
                saver.stop()
                time.sleep(3)

                save_state(username, profile_idx, since, until)

                if status == "rate_limited":
                    profile_idx = (profile_idx + 1) % len(directories)
                    logger.warning(f"{profile_dir} hit a rate limit, switching to next profile.")
                    time.sleep(ROTATE_DELAY)
                    break

                if status == "no_more_tweets":
                    logger.info(f"No tweets for {username} in {since} → {until}")
                    continue

                if status == "ok" and saver.last_response_time > 0:
                    logger.info(f"Captured tweets for {username} {since} → {until}")
                else:
                    logger.warning(f"No SearchTimeline responses for {username} {since} → {until}")

            else:
                logger.info(f"Completed all date windows for {username}")
                clear_state(username)
                return


def main():
    try:
        for username in USERNAMES:
            run_with_rotation(AVAILABLE_DIRECTORIES, username)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
