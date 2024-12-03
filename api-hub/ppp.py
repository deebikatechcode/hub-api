import requests
from typing import Optional, Dict, List

def fetch_ppp_data(country_code: str) -> Optional[float]:
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/PA.NUS.PPP?format=json"
    response = requests.get(url)
    
    if response.status_code != 200:
        
        return None

    try:
        data = response.json()
    except ValueError:
        
        return None

    if not data or len(data) < 2 or not isinstance(data[1], list):
        
        return None

    # Sort the data to get the most recent value first
    sorted_data = sorted(data[1], key=lambda x: x['date'], reverse=True)
    
    for entry in sorted_data:
        if entry.get("value") is not None:
            return entry["value"]

    return None

def calculate_ppp(origin_ppp: float, destination_ppp: float, origin_amount: float) -> float:
    return origin_amount * (destination_ppp / origin_ppp)

def get_ppp_data(origin: str, destination: str, origin_amount: float) -> Dict[str, float]:
    origin_ppp = fetch_ppp_data(origin)
    destination_ppp = fetch_ppp_data(destination)

    if origin_ppp is None:
        return {"error": f"PPP data for {origin} not found."}
    
    if destination_ppp is None:
        return {"error": f"PPP data for {destination} not found."}
    
    destination_amount = calculate_ppp(origin_ppp, destination_ppp, origin_amount)
    
    rounded_origin_amount = round(origin_amount)
    rounded_destination_amount = round(destination_amount)
    
    return {
        "originAmount": rounded_origin_amount,
        "destinationAmount": rounded_destination_amount
    }

async def fetch_all_ppp_data(countries: List[str], origin_amount: float) -> Dict[str, Dict[str, float]]:
    results = {}
    for country in countries:
        result = get_ppp_data('IND', country, origin_amount)  
        results[country] = result
    return results

