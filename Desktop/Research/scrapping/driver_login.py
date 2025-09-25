from seleniumbase import Driver
import json, time, base64, gzip, zlib, urllib.parse, re
from threading import Event
import datetime as dat
import os


username = input("Write twitter username: ")

driver = Driver(
    browser="chrome",
    uc=True,
    user_data_dir=f"./twitter_data_dir_{username}",
    log_cdp_events=True,
    uc_cdp_events=True,
)

driver.get('https://x.com/login')

input("Waiting for login... Press Enter when logged in.")

driver.quit()