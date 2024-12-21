import csv
import datetime
import pytz
import requests
import subprocess
import urllib
import uuid

from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


import requests
import os

def lookup(symbol):
    """Look up quote for symbol using IEX Cloud API."""
    # Get API key from environment variable
    api_key = "pk_07ef06cc88e74fc98f2be05e085ed70a"
    if not api_key:
        raise ValueError("API key not found. Set the IEX_API_KEY environment variable.")

    # Prepare API request
    symbol = symbol.upper()

    # IEX Cloud API endpoint for quote data
    url = f"https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={api_key}"

    # Query API
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()
        price = round(float(data['latestPrice']), 2)

        return {
            "name": data['companyName'],
            "price": price,
            "symbol": symbol
        }
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error retrieving data: {e}")
        return None

# Make sure to set the environment variable IEX_API_KEY with your actual API key before running this code.
# You can set the environment variable in your operating system or through your IDE if you are using one.



def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
