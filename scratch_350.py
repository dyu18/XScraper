from seleniumbase import Driver
import json, time, base64, gzip, zlib, urllib.parse, re
from threading import Event
import datetime as dat
import os

# === PARAMETRELERİ BURADA DEĞİŞTİRİN ===
username    = "ekrem_imamoglu"
since_date  = "2024-01-01"
until_date  = "2024-01-31"
lang        = "tr"
max_scrolls = 500               # güvenlik limiti
# =======================================

query = f"from:{username} since:{since_date} until:{until_date} lang:{lang}"
search_url = (
    "https://x.com/search?q=" +
    urllib.parse.quote(query, safe="") +
    "&src=typed_query&f=live"
)

available_directories = ['twitter_data_dir_yusuf2029166', 'twitter_data_dir_denizkaraye', 'twitter_data_dir_tuggruldemir', 'twitter_data_dir_uzaykandefer']

driver = Driver(
    browser="chrome",
    uc=True,
    user_data_dir="./{[d for d in available_directories if username in d][i]}",
    log_cdp_events=True,
    uc_cdp_events=True,
)

full_texts, full_objects = [], []
pending_ids              = {}
first_batch_ready        = Event()

# ---------------------------------------------------------
def extract_full_texts(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "full_text":          # 'legacy' içindeki de dâhil
                full_texts.append(v)
            else:
                extract_full_texts(v)
    elif isinstance(obj, list):
        for item in obj:
            extract_full_texts(item)

def extract_tweet_objects(obj):
    if isinstance(obj, dict):
        if "full_text" in obj:
            full_objects.append(obj)
        for v in obj.values():
            extract_tweet_objects(v)
    elif isinstance(obj, list):
        for item in obj:
            extract_tweet_objects(item)

# ---------------------------------------------------------
def on_response(event):
    p   = event.get("params", {})
    url = p.get("response", {}).get("url", "")
    # Hem profile hem search endpoint’i destekleyelim
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
    except Exception as e:
        print(f"getResponseBody error: {e}")
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
        data = json.loads(body)
        prev = len(full_texts)
        extract_full_texts(data)
        extract_tweet_objects(data)
        new  = len(full_texts) - prev
        src  = ("UserTweets" if "UserTweets" in pending_ids[rid]
                else "SearchTl")
        print(f"✓ {src} ⇒ {new} yeni tweet (toplam {len(full_texts)})")
        first_batch_ready.set()
    except json.JSONDecodeError:
        pass

    pending_ids.pop(rid, None)

# ---------------------------------------------------------
driver.add_cdp_listener("Network.responseReceived", on_response)
driver.add_cdp_listener("Network.loadingFinished", on_finished)
driver.execute_cdp_cmd("Network.enable", {})
driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})

# === SAYFAYI AÇ ===
print("Gidilen URL:", search_url)
driver.get(search_url)
time.sleep(2)   
driver.refresh()  # Sayfayı yenileyelim


if not first_batch_ready.wait(timeout=15):
    print("İlk veri gelmedi, ama kaydırmaya devam ediyorum…")

# === KAYDIRMA DÖNGÜSÜ ===
no_new_scrolls = 0            
for i in range(max_scrolls):
    prev_count = len(full_objects)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2.5)                
    if len(full_objects) == prev_count:
        no_new_scrolls += 1
        if no_new_scrolls >= 3:     
            print(f"Üst üste 3 kaydırmada yeni tweet gelmedi, işlem sonlandırılıyor…")
            break
    else:
        no_new_scrolls = 0           
    
os.makedirs("outputs", exist_ok=True)
timestamp = dat.datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"user_tweets_full_objects_{timestamp}.json"
filepath = os.path.join("outputs", filename)

last_saved = full_objects[-1].get("created_at") or full_objects[-1].get("date")

output_data = {
    "last_saved_tweet_date": last_saved,
    "tweets": full_objects
}

with open(filepath, "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"{len(full_objects)} tweet objesi kaydedildi → user_tweets_full_objects_{timestamp}.json")


print(f"Son kaydedilen tweet tarihi: {last_saved}")

driver.quit()