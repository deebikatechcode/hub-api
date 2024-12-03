import httpx

async def fetch_country_data():

    async with httpx.AsyncClient() as client:
        response = await client.get("https://restcountries.com/v3.1/all")
        countries_data = response.json()

    
    country_data = [
        {
            "name": country.get("name", {}).get("common"),
            "flag": country.get("cca2").lower(),  
            "code": country.get("cca2").upper(),  
            "currency": list(country.get("currencies", {}).keys())[0] if country.get("currencies") else None, 
            "symbol": list(country.get("currencies", {}).values())[0].get("symbol") if country.get("currencies") else None  
        }
        for country in countries_data
    ]

    return {"country_data": country_data}
