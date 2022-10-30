import requests
import pandas as pd
from datetime import date, datetime, timedelta
from twilio.rest import Client

# ---CHANGE INFO BELOW--- #

# API Keys
STOCK_API_KEY = "YOUR ALPHAVANTAGE API KEY"
NEWS_API_KEY = "YOUR NEWSAPI.ORG API KEY"

# Twilio Info
account_sid = "YOUR TWILIO ACCOUNT SID"
auth_token = "YOUR TWILIO AUTH TOKEN"
twilio_phone = "YOUR TWILIO PHONE NUMBER"
receiving_number = "YOUR NUMBER TO SEND MESSAGES TO"

# ---END UPDATED INFO--- #


# Date Info
today = date.today()
yesterday = today - timedelta(days=1)
day_before_yesterday = today - timedelta(days=2)
weekday = today.weekday()

# Stock Info
STOCK_ENDPOINT = "https://www.alphavantage.co/query"
STOCK = "TSLA"
QUERY = "TIME_SERIES_DAILY"
stock_params = {"function": QUERY,
                "symbol": STOCK,
                "apikey": STOCK_API_KEY
                }

# News Info
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"
key_words = "Elon Musk AND Tesla"
news_params = {
    "q": key_words,
    "searchIn": "title",
    "from": yesterday,
    "language": "en",
    "sortBy": "popularity",
    "apiKey": NEWS_API_KEY
}


def send_message(account_id: str, acct_token: str, news_article: str = None):
    """Send news from the Twilio Phone"""
    client = Client(account_id, acct_token)
    message = client.messages \
        .create(
        body=f"Test Message {news_article}",
        from_=twilio_phone,
        to=receiving_number,
    )


def msg_formatter(news: dict, price_change: float) -> str:
    if price_change > 0:
        arrow = "🔺"
    else:
        arrow = "🔻"
    msg = f"""{STOCK}: {arrow}{str(price_change * 100)}%\n
    'Headline': {news['title']}\n
    'Brief': {news['description']} 
    """
    return msg


def filter_stock_price(data: dict) -> list[float]:
    """Parses stock data for the desired most last two days of closing data. If it's the weekend or Monday,
    price data automatically comes from the 'Last Refreshed' date.
    """
    last_refresh = data['Meta Data']['3. Last Refreshed']
    last_refresh_dt = datetime.strptime(last_refresh, '%Y-%m-%d').date()
    refreshed = last_refresh_dt - timedelta(days=1)
    daily_data = data['Time Series (Daily)']

    if today.weekday() >= 5 or today.weekday() == 0:  # Checks if it is the weekend or Monday
        yesterday_price = daily_data[last_refresh]['4. close']
        day_before_price = daily_data[str(refreshed)]['4. close']
    else:
        yesterday_price = daily_data[str(yesterday)]['4. close']
        day_before_price = daily_data[str(day_before_yesterday)]['4. close']

    return [float(yesterday_price), float(day_before_price)]


def percent_price_change(recent_prices: list[float]) -> float:
    """Converts prices to a Pandas series and determines the percent change between the days.
    Results are rounded to five decimal places.
    """
    price_series = pd.Series(recent_prices)
    change = price_series.pct_change()[1]
    pct_change = round(change * 100, 2)
    return pct_change


class RequestData:
    """A basic request class to return data from APIs"""

    def __init__(self, api_url: str, params: dict):
        self.api_url = api_url
        self.params = params

    def get_request(self) -> dict:
        response = requests.get(self.api_url, self.params)
        response.raise_for_status()
        return response.json()


stock_request = RequestData(STOCK_ENDPOINT, stock_params)
stock_data = stock_request.get_request()
stock_prices = filter_stock_price(stock_data)
percent_change = percent_price_change(stock_prices)

if abs(percent_change) >= 5.0:
    news_request = RequestData(NEWS_ENDPOINT, news_params)
    news_data = news_request.get_request()

    for article in news_data['articles'][:3]:
        msg = msg_formatter(article, percent_change)
        send_message(account_sid, auth_token, msg)
