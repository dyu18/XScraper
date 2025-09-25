## Script that scrapes tweets from users between since and until dates ##
## Sat 5 July 2025 ##

from seleniumbase import Driver
import json, time, base64, gzip, zlib, urllib.parse
from threading import Event
import datetime as dat
from datetime import datetime, timedelta
import os
from itertools import cycle
import random

usernames = [ 
            "medreyata"  # Let's try a different user
            ]


since_date  = "2024-12-01"
until_date  = "2025-07-01"
max_scrolls = 300 
SCROLL_PAUSE_SEC = 1.2  # wait time after each scroll
# =======================================

# Chrome profile directories that contain session cookies
available_directories = [
    'twitter_data_dir_tophaneliomer',  
    'twitter_data_dir_verdacokhakim',
    'twitter_data_dir_aligorc',
    'twitter_data_dir_denizkaraye',
    'twitter_data_dir_fatih_skan78764',
    'twitter_data_dir_mefesalk',
    'twitter_data_dir_tuggruldemir',
    'twitter_data_dir_uzaykandefer',
    'twitter_data_dir_yusuf2029166',
]

###############################################################################
#  Helper functions
###############################################################################
def build_search_url(until_date: str) -> str:
    """Generates search URL with given until_date."""
    query = f"from:{username} since:{since_date} until:{until_date}"
    print(f"Search query: {query}")
    return (
        "https://x.com/search?q=" +
        urllib.parse.quote(query, safe="") +
        "&src=typed_query&f=live"
    )

def make_driver(profile_dir: str) -> Driver:
    """Creates new SeleniumBase Driver with given profile directory."""
    return Driver(
        browser="chrome",
        uc=True,
        user_data_dir=f"./{profile_dir}",
        log_cdp_events=True,
        uc_cdp_events=True,
    )

def save_output(tweets: list[dict]) -> None:
    """Saves collected tweets to outputs/ folder as JSON."""
    os.makedirs("control_group_outputs", exist_ok=True)
    timestamp = dat.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{username}_full_objects_{timestamp}.json"
    filepath  = os.path.join("control_group_outputs", filename)

    last_saved = tweets[-1]["legacy"]["created_at"]  # required; otherwise KeyError
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            {
                "last_saved_tweet_date": last_saved,
                "tweets": tweets,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"{len(tweets)} tweet objects saved → {filename}")
    print(f"Last saved tweet date: {last_saved}")



def append_output(filepath: str, tweets: list[dict]) -> None:
    """
    Appends new tweet objects to an existing JSON file.
    If file doesn't exist, creates new one like save_output.
    """
    filepath = os.path.join("outputs", filepath)
    dirpath = os.path.dirname(filepath)
    if os.path.exists(filepath):
        # Load existing content
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        existing = data.get("tweets", [])
        combined = existing + tweets
    else:
        # Act like new file
        combined = tweets
        data = {}

    last_saved = combined[-1]["legacy"]["created_at"]  # required; otherwise KeyError
    data.update({
        "last_saved_tweet_date": last_saved,
        "tweets": combined,
    })
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{len(tweets)} tweets added → {os.path.basename(filepath)}")
    print(f"Current last tweet date: {last_saved}")

###############################################################################
#  Main scraping function (runs once per profile)
###############################################################################
def scrape_with_driver(driver: Driver, search_url: str,
                       seen_ids: set[str]) -> tuple[bool, list[dict]]:
    """
    Performs maximum max_scrolls scrolling with given driver & search_url.
    * blocked  : True  → rate-limit / "Something went wrong" occurred
                 False → normal termination (all tweets received)
    * session_objects : new tweet objects collected in this session
    """
    full_objects_session: list[dict] = []
    pending_ids   : dict[str, str] = {}
    first_batch_ready = Event()

    # -------------------------- Extract tweets from JSON ----------------- #

    def extract_tweet_objects(obj):
        if isinstance(obj, dict):
            typename = obj.get("__typename")
            
            # Check two different tweet structures
            if typename == "Tweet" and obj.get("legacy", {}).get("created_at"):
                tid = obj.get("rest_id") or obj.get("id_str") or obj.get("id")
                if tid and tid not in seen_ids:
                    seen_ids.add(tid)
                    full_objects_session.append(obj)
                   
            
            # Also check tweets inside TimelineTimelineItem wrapper
            elif typename == "TweetWithVisibilityResults":
                tweet_obj = obj.get("tweet", {})
                legacy_data = tweet_obj.get("legacy", {})
                # Tweet inside TweetWithVisibilityResults may not have __typename, check rest_id
                tid = tweet_obj.get("rest_id") or tweet_obj.get("id_str") or tweet_obj.get("id")
                if tid and legacy_data.get("created_at") and tid not in seen_ids:
                    seen_ids.add(tid)
                    full_objects_session.append(tweet_obj)

            for v in obj.values():
                extract_tweet_objects(v)

        elif isinstance(obj, list):
            for item in obj:
                extract_tweet_objects(item)

    # --------------------------- CDP Event listeners ------------------- #
    def on_response(event):
        p   = event.get("params", {})
        url = p.get("response", {}).get("url", "")
        if "UserTweets" in url or "SearchTimeline" in url:
            pending_ids[p["requestId"]] = url

    def on_finished(event):
        p   = event.get("params", {})
        rid = p.get("requestId")
        if rid not in pending_ids:
            return
        
        try:
            body_obj = driver.execute_cdp_cmd(
                "Network.getResponseBody", {"requestId": rid}
            )
        except Exception:
            pending_ids.pop(rid, None)
            return

        body = body_obj.get("body", "")
        if body_obj.get("base64Encoded"):
            raw = base64.b64decode(body)
            for decompress in (
                lambda x: gzip.decompress(x),
                lambda x: zlib.decompress(x, 16 + zlib.MAX_WBITS),
                lambda x: x,
            ):
                try:
                    body = decompress(raw).decode("utf-8")
                    break
                except Exception:
                    pass

        try:
            prev_count = len(full_objects_session)
            parsed_json = json.loads(body)
            extract_tweet_objects(parsed_json)
            new_count = len(full_objects_session) - prev_count
            
            first_batch_ready.set()
        except json.JSONDecodeError:
            print("JSON parse error")
            pass

        pending_ids.pop(rid, None)

    # --------------------------- Driver preparation -------------------------- #
    driver.add_cdp_listener("Network.responseReceived", on_response)
    driver.add_cdp_listener("Network.loadingFinished", on_finished)
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})

    print("Navigated to URL:", search_url)
    driver.get(search_url)
    time.sleep(10)  # Increased wait time
    driver.refresh()  # Really refresh the 'Latest' tab
    
    # # Wait for first batch
    # print("Waiting for first tweet batch...")
    # if first_batch_ready.wait(timeout=10):  # wait 10 seconds
    #     print(f"First batch arrived, {len(full_objects_session)} tweets loaded")
    # else:
    #     print("First batch timeout - continuing")
    
    # time.sleep(1)  # Extra wait for any remaining responses

    try:
        driver.find_element(
            "xpath",
            "//span[contains(text(),'Something went wrong') or "
            "contains(text(),'Something went wrong')]"
        )
        blocked = True
        print("Rate-limit: 'Something went wrong' detected in interface.")
        return True, full_objects_session
    except Exception:
    # If element doesn't exist, do nothing, continue
        pass

    # ---------------------------- Scroll loop --------------------------- #
    no_new_scrolls = 0
    blocked        = False
    
    print(f"Tweet count before scroll: {len(full_objects_session)}")

    for scroll_num in range(max_scrolls):
        prev_count = len(full_objects_session)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);") 
        time.sleep(SCROLL_PAUSE_SEC)
        
        # Wait a bit more for responses to arrive
        time.sleep(0.5)

        # How many new tweets came after scroll?
        new_count = len(full_objects_session) - prev_count
        if new_count > 0:
            print(f"✓ Scroll {scroll_num+1} ⇒ {new_count} new tweets (session total {len(full_objects_session)})")

        # Did new tweets arrive?
        if len(full_objects_session) == prev_count:
            no_new_scrolls += 1
            if no_new_scrolls >= 3:
                # No new tweets in 3 consecutive scrolls → check if blocked or finished
                try:
                    driver.find_element(
                        "xpath",
                        "//span[contains(text(),'Something went wrong') or "
                        "contains(text(),'Something went wrong')]"
                    )
                    blocked = True
                    print("Rate-limit: 'Something went wrong' detected in interface.")
                except Exception:
                    print("No new tweets in 3 consecutive scrolls – probably range completed.")
                break
        else:
            no_new_scrolls = 0

    print(f"New tweets collected in session: {len(full_objects_session)}")
    return blocked, full_objects_session

###############################################################################
#  Profile rotation & main flow
###############################################################################
wait_sec = 3
summary: list[dict] = []
for username in usernames:
    print(f"\n=== Starting process with user: {username} ===")
    # Clean start
    seen_ids: set[str] = set()
    full_objects: list[dict] = []
    # Initial settings for profile rotation
    start_idx = random.randrange(len(available_directories))
    profile_cycle = cycle(available_directories[start_idx:] + available_directories[:start_idx])
    current_until = until_date
    try:
        while True:
            profile_dir = next(profile_cycle)
            print(f"\n=== Continuing with profile directory: {profile_dir} ===")

            search_url = build_search_url(current_until)
            driver     = make_driver(profile_dir)

            try:
                blocked, session_objs = scrape_with_driver(driver, search_url, seen_ids)
            finally:
                driver.quit()

            full_objects.extend(session_objs)

            # ── Completed? ───────────────────────────────────────────────────── #
            if not blocked:
                print("No block → Tweet scraping process completed.")
                summary.append({
                    'username': username,
                    'count': len(full_objects),
                    'status': 'success'
                })
                break

            # ── Rate-limit: update until_date + wait + switch to other profile ─────── #
            if session_objs:  # if we have data from session
                raw_date = session_objs[-1]["legacy"]["created_at"]  # required; otherwise KeyError
                # "created_at" example: "Thu Mar 13 09:59:29 +0000 2025"
                last_dt  = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %z %Y").replace(tzinfo=None)
                current_until = (last_dt + timedelta(days=1)).date().isoformat()
                print(f"Rate-limit → new until_date: {current_until}")

            print(f"Waiting {wait_sec} seconds, then switching to other profile…")
            time.sleep(wait_sec)

        ###############################################################################
        #  SAVE
        ###############################################################################

        if full_objects: 
            #append_output("kilavuzyayin_full_objects_20250704_145846.json", full_objects)
            save_output(full_objects)
        else:
            print("No tweets could be collected.")
    except Exception as e:
        print(f"Unexpected error occurred: {e}. Saving available data...")
        summary.append({
            'username': username,
            'count': len(full_objects),
            'status': 'error',
            'error': str(e)
        })
        try:
            save_output(full_objects)
        except Exception as save_err:
            print(f"❌ Error while saving data: {save_err}")

    finally:
            print("\n=== Summary for All Users ===")
            for item in summary:
                print(f"- {item['username']}: {item['status']} — {item['count']} tweet")