# Twitter Tweet Mining Script

A Python script that scrapes tweets from specific users within a date range using Selenium WebDriver and Chrome DevTools Protocol (CDP) to intercept network requests.

## Overview

This script uses SeleniumBase with Chrome WebDriver to navigate Twitter's search interface and collect tweet data by intercepting network responses. It implements profile rotation to handle rate limiting and uses multiple Chrome profiles to maintain session persistence.

## Features

- **Date Range Scraping**: Scrapes tweets between specified `since` and `until` dates
- **Profile Rotation**: Automatically switches between multiple Chrome profiles to avoid rate limits
- **Network Interception**: Uses Chrome DevTools Protocol to capture tweet data from network responses
- **Rate Limit Handling**: Automatically adjusts date ranges when rate limited
- **Session Persistence**: Uses Chrome user data directories to maintain login sessions
- **JSON Output**: Saves collected tweets in structured JSON format

## Prerequisites

### Required Python Packages

```bash
pip install seleniumbase
```

### Chrome Profiles Setup

Before running the script, you need to set up Chrome profiles for each Twitter account:

1. Create directories for each profile in the script's directory:(I didn't add the directories for security reasons run driver_login, login the user on twitter and end the session, it automatically creates the directory. Repeat it for each account)

   ```
   twitter_data_dir_username1/
   twitter_data_dir_username2/
   twitter_data_dir_username3/
   ...
   ```

2. Manually log into Twitter in each profile directory using Chrome:

   ```bash
   # Example for one profile
   google-chrome --user-data-dir=./twitter_data_dir_username1
   ```

3. Log into Twitter and ensure the session is saved

## Configuration

### Basic Settings

```python
usernames = [
    "medreyata"  # Add target usernames here
]

since_date = "2024-12-01"  # Start date (YYYY-MM-DD)
until_date = "2025-07-01"  # End date (YYYY-MM-DD)
max_scrolls = 300          # Maximum scroll attempts per session
SCROLL_PAUSE_SEC = 1.2     # Wait time between scrolls
```

### Profile Directories

Update the `available_directories` list with your Chrome profile directories:

```python
available_directories = [
    'twitter_data_dir_tophaneliomer',
    'twitter_data_dir_verdacokhakim',
    'twitter_data_dir_aligorc',
    # Add your profile directories here
]
```

## Usage

1. **Setup Chrome Profiles**: Follow the prerequisites section above
2. **Configure Settings**: Update usernames, dates, and profile directories
3. **Run the Script**:
   ```bash
   python tweet_mining.py
   ```

## Output

The script creates JSON files in the `control_group_outputs/` directory with the following structure:

```json
{
  "last_saved_tweet_date": "Thu Mar 13 09:59:29 +0000 2025",
  "tweets": [
    {
      "rest_id": "1234567890",
      "legacy": {
        "created_at": "Thu Mar 13 09:59:29 +0000 2025",
        "full_text": "Tweet content here..."
        // ... other tweet data
      }
    }
  ]
}
```

## How It Works

### 1. Search URL Generation

- Constructs Twitter search URLs with user and date filters
- Uses URL encoding for proper query formatting

### 2. Profile Rotation

- Cycles through available Chrome profiles
- Each profile maintains its own Twitter session
- Helps avoid rate limiting by distributing requests

### 3. Network Interception

- Uses Chrome DevTools Protocol (CDP) to listen for network responses
- Intercepts responses from `UserTweets` and `SearchTimeline` endpoints
- Extracts tweet objects from JSON responses

### 4. Tweet Extraction

- Parses JSON responses to find tweet objects
- Handles different tweet structures (`Tweet` and `TweetWithVisibilityResults`)
- Deduplicates tweets using unique IDs

### 5. Rate Limit Handling

- Detects rate limiting by checking for "Something went wrong" messages
- Automatically adjusts the `until_date` to continue from where it left off
- Switches to different profiles when rate limited

## ⚠️ Known Issues

### 1. CDP Listener Problem (Critical)

**Issue**: After the first run, CDP listeners may not work properly on subsequent runs, causing the script to fail to capture network responses.

**Symptoms**:

- Script runs but collects no tweets
- Network responses are not intercepted
- No error messages, but empty results

**Workaround**:

- **Create a new virtual environment for each run**
- This appears to be related to CDP listener state persistence
- The issue may be environment-specific but affects reliability

**Example setup for each run**:

```bash
# Create new virtual environment
python -m venv tweet_mining_env
source tweet_mining_env/bin/activate  # On Windows: tweet_mining_env\Scripts\activate

# Install dependencies
pip install seleniumbase

# Run script
python tweet_mining.py

# Deactivate and remove environment after use
deactivate
rm -rf tweet_mining_env
```

### 2. Twitter Structure Changes

**Issue**: Twitter frequently changes their internal data structures and API responses.

**Impact**:

- Tweet extraction may fail
- New tweet formats may not be recognized
- Network endpoint URLs may change

**Mitigation**:

- Monitor script output for extraction failures
- Update the `extract_tweet_objects` function when new structures are detected
- Check for changes in network request patterns

### 3. Rate Limiting

**Issue**: Twitter has aggressive rate limiting that can block profiles.

**Solutions**:

- Use multiple profiles (already implemented)
- Increase wait times between requests
- Reduce `max_scrolls` per session
- Use residential proxies if needed

## Troubleshooting

### No Tweets Collected

1. Check if CDP listeners are working (see Known Issues #1)
2. Verify Chrome profiles are logged into Twitter
3. Check if date range contains tweets
4. Monitor console output for error messages

### Rate Limiting

1. Increase `wait_sec` between profile switches
2. Reduce `max_scrolls` per session
3. Add more Chrome profiles
4. Check if profiles are properly logged in

### Profile Issues

1. Ensure each profile directory exists
2. Verify Twitter login sessions are active
3. Test profiles manually in Chrome
4. Clear profile data if sessions are corrupted

## Code Structure

### Main Functions

- `build_search_url()`: Generates Twitter search URLs
- `make_driver()`: Creates SeleniumBase driver with profile
- `save_output()`: Saves collected tweets to JSON
- `append_output()`: Appends tweets to existing JSON file
- `scrape_with_driver()`: Main scraping logic with CDP interception

### Key Components

- **CDP Event Listeners**: Capture network responses
- **Tweet Extraction**: Parse JSON for tweet objects
- **Profile Rotation**: Switch between Chrome profiles
- **Rate Limit Detection**: Handle Twitter's blocking mechanisms

## Contributing

When contributing to this script:

1. Test with fresh virtual environments
2. Monitor for Twitter structure changes
3. Update documentation for new features
4. Report any CDP listener issues

## License

This script is for educational and research purposes. Please respect Twitter's Terms of Service and rate limits when using this tool.
