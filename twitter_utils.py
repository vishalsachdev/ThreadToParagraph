import os
import re
import base64
import requests
from urllib.parse import urlparse, parse_qs

TWITTER_API_KEY = os.environ['TWITTER_API_KEY']
TWITTER_API_SECRET = os.environ['TWITTER_API_SECRET']

def get_bearer_token():
    """Get Twitter API bearer token"""
    auth_url = "https://api.twitter.com/oauth2/token"
    credentials = base64.b64encode(f"{TWITTER_API_KEY}:{TWITTER_API_SECRET}".encode('utf-8')).decode('utf-8')
    auth_headers = {
        'Authorization': f'Basic {credentials}',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }
    auth_data = {'grant_type': 'client_credentials'}
    
    response = requests.post(auth_url, headers=auth_headers, data=auth_data)
    if response.status_code != 200:
        error_msg = response.json().get('error_description', 'Authentication failed')
        raise Exception(f"Twitter API authentication failed: {error_msg}")
    return response.json()['access_token']

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

def validate_tweet_data(data, required_fields):
    """Validate tweet data contains required fields"""
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required fields in tweet data: {', '.join(missing_fields)}")
    return True

def handle_api_error(response):
    """Handle Twitter API error responses"""
    error_data = response.json()
    if 'errors' in error_data:
        error = error_data['errors'][0]
        error_code = error.get('code', 'unknown')
        error_msg = error.get('message', 'Unknown error')
        raise Exception(f"Twitter API error {error_code}: {error_msg}")
    else:
        raise Exception("Unknown Twitter API error")

def fetch_thread(url, author_only=False):
    """Fetch and process thread from Twitter API"""
    try:
        bearer_token = get_bearer_token()
        tweet_id = extract_tweet_id(url)
        
        # First, get the initial tweet details
        api_url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        headers = {'Authorization': f'Bearer {bearer_token}'}
        params = {
            'tweet.fields': 'conversation_id,author_id,created_at,in_reply_to_user_id',
            'expansions': 'referenced_tweets.id,author_id'
        }
        
        response = requests.get(api_url, headers=headers, params=params)
        if response.status_code != 200:
            handle_api_error(response)
            
        tweet_data = response.json()
        
        # Validate required fields
        validate_tweet_data(tweet_data['data'], ['conversation_id', 'author_id'])
        conversation_id = tweet_data['data']['conversation_id']
        original_author_id = tweet_data['data']['author_id']
        
        # Fetch quote tweets and replies
        quotes_url = f"https://api.twitter.com/2/tweets/{tweet_id}/quote_tweets"
        quotes_params = {
            'tweet.fields': 'conversation_id,author_id,created_at,in_reply_to_user_id',
            'expansions': 'referenced_tweets.id,author_id',
            'max_results': 100
        }
        
        response = requests.get(quotes_url, headers=headers, params=quotes_params)
        if response.status_code != 200:
            handle_api_error(response)
            
        quotes_data = response.json()
        all_tweets = [tweet_data['data']]  # Start with original tweet
        
        if 'data' in quotes_data:
            thread_tweets = quotes_data['data']
            # Filter quotes by conversation_id and author_id if needed
            for tweet in thread_tweets:
                if tweet['conversation_id'] == conversation_id:
                    if not author_only or tweet['author_id'] == original_author_id:
                        all_tweets.append(tweet)
        
        if not all_tweets:
            return tweet_data['data']['text']  # Return single tweet if no thread found
            
        # Sort tweets by created_at
        all_tweets.sort(key=lambda x: x['created_at'])
        
        # Combine tweets into readable text
        thread_text = ""
        for tweet in all_tweets:
            text = tweet['text']
            # Clean up text (remove URLs, mentions, etc)
            text = re.sub(r'https://\S+', '', text)
            text = re.sub(r'@\w+', '', text)
            text = text.strip()
            thread_text += f"{text}\n\n"
        
        return thread_text.strip()
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {str(e)}")
    except KeyError as e:
        raise Exception(f"Unexpected API response format: Missing field {str(e)}")
    except ValueError as e:
        raise Exception(str(e))
    except Exception as e:
        raise Exception(f"Error processing thread: {str(e)}")
