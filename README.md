# X (Twitter) Tweet Mining Script

A Python script that scrapes tweets from specific users within a date range using undetected-chromedriver and Chrome DevTools Protocol (CDP) to intercept network requests.

## Overview

This script uses undetected-chromedriver with Chrome WebDriver to navigate X's search interface and collect tweet data by intercepting network responses. It implements profile rotation to handle rate limiting, uses multiple Chrome profiles to maintain session persistence, and includes advanced features like state persistence and structured logging.

## Features

- **Date Range Scraping**: Scrapes tweets between specified `since` and `until` dates with configurable date windows
- **Profile Rotation**: Automatically switches between multiple Chrome profiles to avoid rate limits
- **Network Interception**: Uses Chrome DevTools Protocol to capture SearchTimeline responses from network requests
- **Rate Limit Handling**: Automatically detects rate limits and switches profiles
- **Session Persistence**: Uses Chrome user data directories to maintain login sessions
- **State Persistence**: Resumes crawling from where it left off after interruptions
- **Structured Logging**: Comprehensive logging with file rotation and console output
- **Undetected Chrome**: Uses undetected-chromedriver to avoid detection
- **Threaded CDP Listener**: Background thread captures network responses efficiently
- **Organized Output**: Saves responses in per-user, per-date-window subdirectories

## Prerequisites

### Required Python Packages

```bash
pip install undetected-chromedriver
```

### Chrome Profiles Setup

Before running the script, you need to set up Chrome profiles for each X (Twitter) account:

1. Create directories for each profile in the script's directory:

   ```
   twitter_data_dir_username1/
   twitter_data_dir_username2/
   twitter_data_dir_username3/
   ...
   ```

2. Manually log into X (Twitter) in each profile directory using Chrome:

   ```bash
   # Example for one profile
   google-chrome --user-data-dir=./twitter_data_dir_username1
   ```

3. Log into X (Twitter) and ensure the session is saved

## Configuration

### Basic Settings

```python
USERNAMES = ["realDonaldTrump", "elonmusk"]  # Target usernames
SINCE_DATE = "2025-10-01"                   # Start date (YYYY-MM-DD)
UNTIL_DATE = "2025-10-07"                   # End date (YYYY-MM-DD)
DATE_WINDOW_DAYS = 1                        # Days per date window
SCROLLS = 100                               # Maximum scroll attempts per session
SCROLL_PAUSE = 1.2                          # Wait time between scrolls
ROTATE_DELAY = 10                           # Seconds before trying next profile
```

### Profile Directories

Update the `AVAILABLE_DIRECTORIES` list with your Chrome profile directories:

```python
AVAILABLE_DIRECTORIES = [
    "twitter_data_dir_tophaneliomer",
    "twitter_data_dir_verdacokhakim",
    # Add your profile directories here
]
```

### Output and Logging

```python
OUT_DIR = Path("tweet_responses")  # Main output directory
LOG_DIR = Path("logs")             # Log files directory
```

## Usage

1. **Setup Chrome Profiles**: Follow the prerequisites section above
2. **Configure Settings**: Update usernames, dates, and profile directories
3. **Run the Script**:
   ```bash
   python uc_cdp_listener_with_rotation.py
   ```

### State Management

The script automatically saves progress and can resume from interruptions:
- State files are saved as `crawl_state_{username}.json`
- Progress includes current profile index and date window
- State is cleared when crawling completes successfully
- To restart from beginning, delete the state files

## Output

The script creates organized output in the `tweet_responses/` directory with the following structure:

```
tweet_responses/
├── username1/
│   ├── 2025-10-01_2025-10-02/
│   │   ├── resp_1696123456_0.json
│   │   ├── resp_1696123456_1.json
│   │   └── ...
│   └── 2025-10-02_2025-10-03/
│       └── ...
└── username2/
    └── ...
```

Each response file contains the raw SearchTimeline API response with tweet data:

```json
{
  "data": {
    "search_by_raw_query": {
      "search_timeline": {
        "timeline": {
          "instructions": [
            {
              "type": "TimelineAddEntries",
              "entries": [
                {
                  "entryId": "tweet-1234567890",
                  "content": {
                    "entryType": "TimelineTimelineItem",
                    "itemContent": {
                      "tweet_results": {
                        "result": {
                          "rest_id": "1234567890",
                          "legacy": {
                            "created_at": "Thu Mar 13 09:59:29 +0000 2025",
                            "full_text": "Tweet content here..."
                          }
                        }
                      }
                    }
                  }
                }
              ]
            }
          ]
        }
      }
    }
  }
}
```

## How It Works

### 1. Date Window Processing

- Divides the date range into configurable windows (e.g., 1 day chunks)
- Processes each window sequentially to avoid overwhelming the API
- Enables resuming from specific date windows after interruptions

### 2. Search URL Generation

- Constructs X search URLs with user and date filters
- Uses URL encoding for proper query formatting
- Format: `https://x.com/search?q=from:username since:date until:date&src=typed_query&f=live`

### 3. Profile Rotation

- Cycles through available Chrome profiles automatically
- Each profile maintains its own X session
- Switches profiles when rate limits are detected
- Includes configurable delay between profile switches

### 4. Network Interception

- Uses Chrome DevTools Protocol (CDP) to listen for network responses
- Background thread (`CDPResponseSaver`) continuously monitors performance logs
- Intercepts responses from `SearchTimeline` endpoints specifically
- Saves raw response bodies as JSON files

### 5. Rate Limit Detection

- Monitors response content for "rate limit exceeded" messages
- Automatically stops current profile and switches to next one
- Implements exponential backoff with configurable delays

### 6. State Persistence

- Saves progress after each date window completion
- Tracks current profile index and date window
- Enables resuming from exact interruption point
- Clears state when crawling completes successfully

### 7. Structured Logging

- Comprehensive logging with file rotation (5MB max, 30 backups)
- Console and file output with timestamps and thread information
- Logs profile switches, rate limits, and response captures

## ⚠️ Known Issues

### 1. X Structure Changes

**Issue**: X (Twitter) frequently changes their internal data structures and API responses.

**Impact**:

- SearchTimeline endpoint structure may change
- New tweet formats may not be recognized
- Network endpoint URLs may change

**Mitigation**:

- Monitor script output for extraction failures
- Check logs for "No tweets found" messages
- Update the response parsing logic when new structures are detected
- Monitor for changes in network request patterns

### 2. Rate Limiting

**Issue**: X has aggressive rate limiting that can block profiles.

**Solutions**:

- Use multiple profiles (already implemented)
- Increase `ROTATE_DELAY` between profile switches
- Reduce `SCROLLS` per session
- Use residential proxies if needed
- Monitor logs for rate limit detection

### 3. Profile Session Issues

**Issue**: Chrome profiles may lose login sessions or become corrupted.

**Symptoms**:

- Script runs but gets redirected to login page
- No SearchTimeline responses captured
- Profile switching occurs frequently

**Solutions**:

- Re-login to affected profiles manually
- Clear profile data if sessions are corrupted
- Test profiles manually in Chrome before running script
- Ensure profiles are properly logged into X

### 4. Network Interception Reliability

**Issue**: CDP network interception may occasionally miss responses.

**Symptoms**:

- Some date windows show no responses despite tweets existing
- Inconsistent response capture

**Mitigation**:

- Increase `SCROLL_PAUSE` time
- Monitor logs for response capture patterns
- Consider running problematic date windows again

## Troubleshooting

### No Responses Collected

1. Check if Chrome profiles are logged into X
2. Verify the date range contains tweets for the target user
3. Monitor log files for error messages and response capture patterns
4. Check if SearchTimeline endpoints are being intercepted
5. Ensure undetected-chromedriver is working properly

### Rate Limiting

1. Increase `ROTATE_DELAY` between profile switches
2. Reduce `SCROLLS` per session
3. Add more Chrome profiles to `AVAILABLE_DIRECTORIES`
4. Check if profiles are properly logged into X
5. Monitor logs for rate limit detection messages

### Profile Issues

1. Ensure each profile directory exists and is accessible
2. Verify X login sessions are active in each profile
3. Test profiles manually in Chrome before running script
4. Clear profile data if sessions are corrupted
5. Check for Chrome profile lock files

### State Management Issues

1. Check for `crawl_state_{username}.json` files
2. Delete state files to restart from beginning
3. Verify state files contain valid JSON
4. Monitor logs for state save/load operations

### Logging Issues

1. Check if `logs/` directory exists and is writable
2. Monitor log file size and rotation
3. Check console output for immediate feedback
4. Verify log levels are appropriate

## Code Structure

### Main Classes

- `UCSession`: Context manager for undetected-chromedriver with Chrome profiles
- `CDPResponseSaver`: Background thread that captures SearchTimeline responses

### Main Functions

- `build_search_url()`: Generates X search URLs with date filters
- `daterange_chunks()`: Divides date range into configurable windows
- `run_with_rotation()`: Main orchestration with profile rotation
- `scroll_and_capture()`: Handles scrolling and response capture
- `save_state()` / `load_state()`: State persistence management

### Key Components

- **CDP Network Interception**: Captures SearchTimeline API responses
- **Profile Rotation**: Automatic switching between Chrome profiles
- **Rate Limit Detection**: Monitors response content for rate limits
- **State Persistence**: Resumes from interruption points
- **Structured Logging**: Comprehensive logging with file rotation

## Contributing

When contributing to this script:

1. Test with multiple Chrome profiles
2. Monitor for X structure changes
3. Update documentation for new features
4. Report any CDP listener or rate limiting issues
5. Test state persistence functionality

## License

This script is for educational and research purposes. Please respect X's Terms of Service and rate limits when using this tool.
