import json
import os
import openai
from dotenv import find_dotenv, load_dotenv
import requests
import logging
import time
from datetime import datetime

load_dotenv()

news_api_key = os.getenv("NEWS_API_KEY")
# print(news_api_key)

client = openai.OpenAI()
model = "gpt-3.5-turbo-16k"


def get_news(topic):
    url = (
        f"https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}&pageSize=5"
    )
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = json.dumps(response.json(), indent=4) # Serialize obj to a JSON formatted str
            # Now I am gonna convert that string to a python dictionary so I am gonna be able to access its fields easily
            news = json.loads(news)
            data = news
            
            # Access all the fields == Loop through
            status = data["status"]
            totalResults = data["totalResults"]
            articles = data["articles"]
            
            final_news = []
            # Loop through the articles
            for article in articles:
                source_name = article["source"]["name"]
                author = article["author"]
                title = article["title"]
                description = article["description"]
                url = article["url"]
                content = article["content"]
                
                title_descritiopn = f"""
                    Title: {title},
                    Author: {author},
                    Source: {source_name},
                    Description: {description}
                    URL: {url}
                """
                final_news.append(title_descritiopn)
                
            return final_news
        
        else:
            #print(response.status_code)
            return []
            
    
    except requests.exceptions.RequestException as e:
        print("Error occured during api request,", e)
        
        


def main():
    news = get_news("bitcoin")
    print(news[0])

if __name__ == "__main__":
    main()