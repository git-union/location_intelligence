import os
import json
import requests
import google.generativeai as genai

# API Keys from .env file
GOOGLE_API_KEY = 
GEMINI_API_KEY = 

genai.configure(api_key=GEMINI_API_KEY)

def get_google_places(zipcode, store_type):
    """Fetches nearby stores and their details from Google Places API (New Text Search)."""
    lat, lon = get_lat_lon(zipcode)
    if lat is None or lon is None:
        return {"error": "Could not fetch location data."}

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.primaryType,places.types,places.rating"
    }
    data = {
        "textQuery": f"{store_type} in {zipcode}"
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_lat_lon(zipcode):
    """Fetches latitude and longitude for a given ZIP code using Google Geocoding API."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={zipcode}&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        response_json = response.json()

        if response_json["status"] == "OK":
            location = response_json["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
        else:
            print(f"Geocoding failed: {response_json['status']}")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching geocoding data: {e}")
        return None, None

def get_weather_data(zipcode):
    """Fetches real-time weather data from Open-Meteo API based on latitude & longitude."""
    lat, lon = get_lat_lon(zipcode)
    if lat is None or lon is None:
        return {"error": "Could not fetch location data."}

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    try:
        response = requests.get(url)
        response.raise_for_status()
        response_json = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return {"error": f"Error fetching weather data: {e}"}
    return response_json

def fetch_data(zipcode, store_type):
    """Fetches data for a given ZIP code and combines results."""
    print(f"Fetching data for ZIP Code: {zipcode} and store type: {store_type}...")

    places_data = get_google_places(zipcode, store_type)
    if "error" in places_data:
        return places_data

    stores = []
    for place in places_data.get("places", []):
        stores.append(place) #append the place dictionary directly

    weather_data = get_weather_data(zipcode)

    result = {
        "zipcode": zipcode,
        "stores": stores,
        "weather": weather_data
    }

    return result

def get_campaign_recommendations(data, store_type):
    """Generates campaign recommendations using Gemini API."""
    model = genai.GenerativeModel('gemini-2.0-flash')

    context = f"""
    Based on the following data for a {store_type} in ZIP code {data['zipcode']}:
    Stores: {data['stores']}
    Weather: {data['weather']}

    Generate a list of 10 campaign recommendations. Each recommendation should include:
    - Campaign Title
    - Campaign Description
    - Insight leading to the recommendation
    - Start Date (YYYY-MM-DD)
    - End Date (YYYY-MM-DD)
    - Discount Amount (if applicable)
    """
    try:
        response = model.generate_content(context)
        return response.text
    except Exception as e:
        return f"Error generating campaigns: {e}"

def select_top_campaigns(campaigns_text):
    """Selects the top 5 campaigns from the generated text using Gemini API."""
    model = genai.GenerativeModel('gemini-2.0-flash')

    context = f"""
    From the following list of campaign recommendations, select the top 5 most effective campaigns considering its a mom and pop type small business and present them in a JSON format.

    {campaigns_text}

    Present the result as a JSON array where each element contains:
    - campaign_title
    - campaign_description
    - insight
    - start_date
    - end_date
    - discount_amount
    """
    try:
        response = model.generate_content(context)
        return response.text
    except Exception as e:
        return f"Error selecting top campaigns: {e}"

# Ask user for the ZIP code
zipcode = input("Please enter the ZIP code: ")
store_type = input("Please enter the store type (e.g., Flower store, Art store, Grocery store): ")

# Fetch data for the entered ZIP code
data = fetch_data(zipcode, store_type)

if data and "error" not in data:
    with open("location_insights.json", "w") as f:
        json.dump(data, f, indent=4)
    print("Data saved to location_insights.json")

    campaigns_text = get_campaign_recommendations(data, store_type)
    print("\nGenerated Campaigns:")
    print(campaigns_text)

    top_campaigns_json = select_top_campaigns(campaigns_text)
    print("\nTop 5 Campaigns (JSON):")
    print(top_campaigns_json)

    try:
        top_campaigns_data = json.loads(top_campaigns_json)
        with open("top_campaigns.json", "w") as f:
            json.dump(top_campaigns_data, f, indent=4)
        print("Top campaigns saved to top_campaigns.json")
    except json.JSONDecodeError:
        print("Error: Could not parse top campaigns JSON.")

elif data:
    print(f"Data fetch failed: {data}")
else:
    print("Data fetch failed.")
