#!/usr/bin/env python3
"""
Sample main script that demonstrates how to use the tweet mining functionality
from uc_cdp_listener_with_rotation.py
"""

from uc_cdp_listener_with_rotation import run_with_rotation

# Configuration - Update these values for your use case
AVAILABLE_DIRECTORIES = [
    "twitter_data_dir_tophaneliomer",
    "twitter_data_dir_verdacokhakim",
    # Add your Chrome profile directories here
]

USERNAMES = [
    "realDonaldTrump",
    "elonmusk",
    # Add target usernames here
]

def main():
    """
    Main function that runs the tweet mining for each username
    """
    print("Starting tweet mining process...")
    print(f"Target usernames: {USERNAMES}")
    print(f"Available profiles: {AVAILABLE_DIRECTORIES}")
    
    try:
        for username in USERNAMES:
            print(f"\nProcessing username: {username}")
            run_with_rotation(AVAILABLE_DIRECTORIES, username)
            print(f"Completed processing for {username}")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
