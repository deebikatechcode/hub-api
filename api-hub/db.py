import os
import boto3
from dotenv import load_dotenv
from boto3.resources.base import ServiceResource
import psycopg2

load_dotenv()

def initialize_db() -> ServiceResource:
    ddb = boto3.resource(
        "dynamodb",
        region_name=os.environ.get("AWS_REGION"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )

    return ddb

def initialize_postgresql():
    conn = psycopg2.connect(
        database=os.environ.get("POSTGRES_DB"),
        host=os.environ.get("POSTGRES_HOST"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD")
    )
    return conn
