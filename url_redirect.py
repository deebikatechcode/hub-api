from hashlib import blake2b
from datetime import datetime
from pydantic import BaseModel
from db import initialize_db
from boto3.dynamodb.conditions import Key

class URLRequest(BaseModel):
    long_url: str
dynamodb = initialize_db()
url_table = dynamodb.Table('URLAnalytics')
    
def generate_short_key(long_url: str) -> str:
    """
    Generate a short key for the given URL using blake2b hash.
    """
    short_key = blake2b(long_url.encode(), digest_size=5).hexdigest()
    return short_key
def store_url(long_url: str, short_key: str) -> None:

    url_table.put_item(Item={
        "short_key": short_key,
        "record_type": "URL",
        "long_url": long_url
    })

def log_visitor(short_key: str, visitor_ip: str, visitor_country: str) -> None:
    
    url_table.put_item(Item={
        "short_key": short_key,
        "record_type": f"VISIT#{datetime.utcnow().isoformat()}",
        "visitor_ip": visitor_ip,
        "visitor_country": visitor_country
    })

def get_original_url(short_key: str) -> str:
    
    response = url_table.get_item(
        Key={"short_key": short_key, "record_type": "URL"}
    )
    return response.get("Item", {}).get("long_url")

def get_analytics(short_key: str) -> dict:
    
    response = url_table.query(
        KeyConditionExpression=Key("short_key").eq(short_key) &
                               Key("record_type").begins_with("VISIT#")
    )
    items = response.get("Items", [])
    return {
        "total_visits": len(items),
        "details": items
    }
