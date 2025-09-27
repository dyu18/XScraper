# Strach the tweets of a user from X (Twitter) using SeleniumBase with CDP support
# This script collects tweets from a specific user profile and saves them to a JSON file.
# However after some point(approximately 700 tweets) X inhibits the action.

from seleniumbase import Driver
import json
import time
from datetime import datetime
import base64, gzip, zlib
from threading import Event


username = "ekrem_imamoglu" 

# Initialize driver with CDP support
driver = Driver(
    browser="chrome",
    uc=True,
    user_data_dir='./twitter_data_dir',
    log_cdp_events=True,
    uc_cdp_events=True
)

full_texts = []
full_objects = []  # will store complete tweet dicts
pending_ids = {}
first_batch_ready = Event()  # set after first UserTweets batch

def extract_full_texts(obj):
    if isinstance(obj, dict):
        
        for k, v in obj.items():
            if k == "full_text":
                full_texts.append(v)
            else:
                extract_full_texts(v)
    elif isinstance(obj, list):
        for item in obj:
            extract_full_texts(item)

def extract_tweet_objects(obj):
    """
    Recursively collect every dict that contains a 'full_text' key.
    The entire dict (tweet object) is appended to `full_objects`.
    """
    if isinstance(obj, dict):
        if "full_text" in obj:
            full_objects.append(obj)
        for v in obj.values():
            extract_tweet_objects(v)
    elif isinstance(obj, list):
        for item in obj:
            extract_tweet_objects(item)

def on_response(event):
    p = event.get("params")
    if not p:
        return
    url = p.get("response", {}).get("url", "")
    if "UserTweets" in url:
        pending_ids[p["requestId"]] = url


def on_finished(event):
    p = event.get("params")
    if not p:
        return
    rid = p.get("requestId")
    if rid not in pending_ids:
        return

    try:
        body_obj = driver.execute_cdp_cmd(
            "Network.getResponseBody", {"requestId": rid}
        )
    except Exception as e:
        print(f"getResponseBody error: {e}")
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
        data = json.loads(body)
        prev = len(full_texts)
        extract_full_texts(data)
        extract_tweet_objects(data)
        new = len(full_texts) - prev
        print(f"✓ UserTweets ⇒ {new} new tweets (total {len(full_texts)} | objects {len(full_objects)})")
        if not first_batch_ready.is_set():
            first_batch_ready.set()
    except json.JSONDecodeError:
        print("JSON decode error")

    pending_ids.pop(rid, None)

# Add CDP listener
driver.add_cdp_listener("Network.responseReceived", on_response)
driver.add_cdp_listener("Network.loadingFinished", on_finished)

# Enable network tracking
driver.execute_cdp_cmd("Network.enable", {})
driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
time.sleep(5)
# Open the page
driver.get(f'https://x.com/{username}') # Replace with the user profile URL you waant to scrape
time.sleep(3)  # Wait for initial content to load
driver.refresh()  
time.sleep(3)  
if not first_batch_ready.wait(timeout=10):
    print("İlk UserTweets gelmedi, yine de devam ediyorum...")

# Continuously scroll until no new tweets are loaded
for i in range(500):  # Limit to 100 scrolls to prevent infinite loop
    prev_count = len(full_objects)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    print("Scrolled, waiting for content...")
    time.sleep(3)  # wait for new tweets to load
    
    # Break if no new tweet objects were added
    # if len(full_objects) == prev_count:
    #     print("No more new tweets found, stopping scroll.")
    #     break

# Save results
with open(f"user_tweets_{username}.json", "w", encoding="utf-8") as f:
    json.dump(full_texts, f, ensure_ascii=False, indent=2)
    print(f"\n{'='*50}\nSaved {len(full_texts)} tweets to user_tweets.json\n{'='*50}")

# Save full tweet objects
with open(f"user_tweets_full_objects_{username}.json", "w", encoding="utf-8") as f:
    json.dump(full_objects, f, ensure_ascii=False, indent=2)
    print(f"{'='*50}\nSaved {len(full_objects)} tweet objects to user_tweets_full_objects.json\n{'='*50}")

driver.quit()