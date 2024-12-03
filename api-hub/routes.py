from fastapi import HTTPException
from db import initialize_db

async def get_all_routes_function():
    try:
       
        dynamodb = initialize_db()
        table = dynamodb.Table('APICodes')
        
        response = table.scan()
        items = response.get('Items', [])

        # Extract all unique routes from the items
        all_routes = set()
        for item in items:
            routes = item.get('Routes', [])
            all_routes.update(routes)


        return {"routes": list(all_routes)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
