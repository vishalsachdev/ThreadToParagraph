import os
import re
import requests
from urllib.parse import urlparse, parse_qs

TWITTER_API_KEY = os.environ['TWITTER_API_KEY']
TWITTER_API_SECRET = os.environ['TWITTER_API_SECRET']

def get_bearer_token():
    """Get Twitter API bearer token"""
    auth_url = "https://api.twitter.com/oauth2/token"
    auth_headers = {
        'Authorization': f'Basic {TWITTER_API_KEY}:{TWITTER_API_SECRET}',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }
    auth_data = {'grant_type': 'client_credentials'}
    
    response = requests.post(auth_url, headers=auth_headers, data=auth_data)
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def extract_tweet_id(url):
    """Extract tweet ID from URL"""
    parsed = urlparse(url)
    if 'twitter.com' not in parsed.netloc and 'x.com' not in parsed.netloc:
        raise ValueError("Not a valid Twitter/X URL")
    
    path_parts = parsed.path.split('/')
    for part in path_parts:
        if part.isdigit():
            return part
    raise ValueError("Could not find tweet ID in URL")

def fetch_thread(url):
    """Fetch and process thread from Twitter API"""
    bearer_token = get_bearer_token()
    if not bearer_token:
        raise Exception("Failed to authenticate with Twitter API")

    tweet_id = extract_tweet_id(url)
    api_url = f"https://api.twitter.com/2/tweets/{tweet_id}/conversation_thread"
    headers = {'Authorization': f'Bearer {bearer_token}'}
    
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to fetch thread from Twitter API")

    tweets = response.json()['data']
    # Sort tweets by conversation thread order
    tweets.sort(key=lambda x: x['conversation_position'])
    
    # Combine tweets into readable text
    thread_text = ""
    for tweet in tweets:
        text = tweet['text']
        # Clean up text (remove URLs, mentions, etc)
        text = re.sub(r'https://\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = text.strip()
        thread_text += f"{text}\n\n"
    
    return thread_text.strip()
