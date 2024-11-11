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

def fetch_thread(url, author_only=False):
    """Fetch and process thread from Twitter API"""
    try:
        bearer_token = get_bearer_token()
        tweet_id = extract_tweet_id(url)
        
        # First, get the conversation ID and author ID from the initial tweet
        api_url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        headers = {'Authorization': f'Bearer {bearer_token}'}
        params = {
            'tweet.fields': 'conversation_id,author_id,created_at,in_reply_to_user_id',
            'expansions': 'referenced_tweets.id'
        }
        
        response = requests.get(api_url, headers=headers, params=params)
        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get('errors', [{'message': 'Unknown error'}])[0].get('message')
            raise Exception(f"Twitter API error: {error_msg}")
            
        tweet_data = response.json()
        conversation_id = tweet_data['data'].get('conversation_id')
        original_author_id = tweet_data['data'].get('author_id')
        
        # Now fetch the entire conversation
        search_url = "https://api.twitter.com/2/tweets/search/recent"
        query = f'conversation_id:{conversation_id}'
        if author_only:
            query += f' from:{original_author_id}'
            
        search_params = {
            'query': query,
            'tweet.fields': 'conversation_id,author_id,created_at,in_reply_to_user_id',
            'max_results': 100,
            'expansions': 'referenced_tweets.id'
        }
        
        response = requests.get(search_url, headers=headers, params=search_params)
        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get('errors', [{'message': 'Unknown error'}])[0].get('message')
            raise Exception(f"Twitter API error: {error_msg}")
            
        tweets = response.json().get('data', [])
        if not tweets:
            return tweet_data['data']['text']  # Return single tweet if no thread found
            
        # Add the original tweet to the beginning if not included
        tweets = [tweet_data['data']] + [t for t in tweets if t['id'] != tweet_id]
            
        # Sort tweets by created_at
        tweets.sort(key=lambda x: x['created_at'])
        
        # Combine tweets into readable text
        thread_text = ""
        for tweet in tweets:
            # Skip tweets from other authors if author_only is True
            if author_only and tweet['author_id'] != original_author_id:
                continue
                
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
        raise Exception(f"Unexpected API response format: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing thread: {str(e)}")
