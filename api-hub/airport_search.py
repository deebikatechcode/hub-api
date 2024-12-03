from fastapi import HTTPException
import pandas as pd
import re


def search_string(s, search):
    return search in str(s).lower()


async def airport_search(param):
    search_df = pd.read_excel("Airport.xlsx").fillna("")
    if search_df is None:
        raise HTTPException(
            status_code=500, detail="Excel file not uploaded or processed")

    # Apply search filters
    if param:
        pattern = re.compile(re.escape(param), re.IGNORECASE)
        search_df = search_df[
            search_df['AIRPORTNAME'].str.contains(pattern, na=False) |
            search_df['CITYNAME'].str.contains(pattern, na=False) |
            search_df['COUNTRYNAME'].str.contains(pattern, na=False)
        ]
        param = str(param).lower()
        # Search for the string 'al' in all columns
        mask = search_df.apply(lambda x: x.map(
            lambda s: search_string(s, param)))

        # Filter the DataFrame based on the mask
        filtered_df = search_df.loc[mask.any(axis=1)]

    result = [
        {
            "Code": row['AIRPORTCODE'],
            "Name": row['AIRPORTNAME'],
            "AirportName": "".join([row['AIRPORTNAME'], " ( ", row['AIRPORTCODE'], " ) "]),
            "City": row['CITYNAME'],
            "Country": row['COUNTRYNAME']
        }
        for _, row in filtered_df.iterrows()
    ]

    return result
