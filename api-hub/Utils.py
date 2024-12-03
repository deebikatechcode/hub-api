from db import initialize_db
import datetime
from fastapi import Request, Response
from starlette.concurrency import iterate_in_threadpool
from random import random
import math
from uuid import uuid4
from db import initialize_postgresql


async def LogRequest(request: Request):
    ddb = initialize_db()
    table = ddb.Table("Logs")
    table.put_item(
        Item={
            "LogId": request.state.LogId,
            "Type": "Request",
            "IP": request.client.host,
            "APICode": request.headers["X-APIKey"],
            "Path": request.scope["path"],
            "ReqHeaders": request.headers,
            "ReqBody": str(await request.body()),
            "ReqMethod": request.method,
            "ReqBaseURL": str(request.base_url),
            "ReqQueryParams": request.query_params,
            "ReqPathParams": request.path_params,
            "ReqURL": str(request.url),
            "ReqReceivedOn": str(datetime.datetime.now()),
        }
    )


async def updateResponse(request: Request, response: Response):
    response_body = [section async for section in response.body_iterator]
    response.body_iterator = iterate_in_threadpool(iter(response_body))
    ddb = initialize_db()
    table = ddb.Table("Logs")
    table.update_item(
        Key={"LogId": request.state.LogId},
        UpdateExpression="set ResHeaders = :resHead, ResBody = :resBody, ResReceivedOn = :resReceived",
        ExpressionAttributeValues={
            ":resHead": response.headers,
            ":resBody": str(response_body[0].decode()),
            ":resReceived": str(datetime.datetime.now()),
        },
        ReturnValues="UPDATED_NEW",
    )


async def UpdateModel(PairId: str, pricing: str):
    ddb = initialize_db()
    table = ddb.Table("Logs")
    Model = SelectModelGroq(pricing)
    table.update_item(
        Key={"LogId": PairId},
        UpdateExpression="set Model = :Model",
        ExpressionAttributeValues={":Model": Model},
        ReturnValues="UPDATED_NEW",
    )
    return Model


def SelectModelGroq(pricing):
    FreeModels = ["llama3-8b-8192", "gemma-7b-it", "llama-3.1-8b-instant"]
    StandardModels = ["mixtral-8x7b-32768", "gemma2-9b-it"]
    PremiumModels = ["llama-3.1-70b-versatile", "llama3-70b-8192"]
    if pricing == "Basic":
        return FreeModels[math.floor(random() * len(FreeModels))]
    elif pricing == "Standard":
        return StandardModels[math.floor(random() * len(StandardModels))]
    elif pricing == "Premium":
        return PremiumModels[math.floor(random() * len(PremiumModels))]


def getPricing(pricing):
    if pricing == "Basic":
        return 0
    elif pricing == "Standard":
        return 1
    elif pricing == "Premium":
        return 2

def format_transcript(transcript):
    formatted_transcript = ""
    for entry in transcript:
        wrapped_text = entry["text"]
        formatted_transcript += wrapped_text + " "
    return formatted_transcript

async def checkLimits(request: Request):
    ddb = initialize_db()
    table = ddb.Table("APICodes")
    data = table.get_item(Key={"key": request.headers["X-APIKey"]})
    if (
        request.headers["X-Pricing"] == "Standard"
        or request.headers["X-Pricing"] == "Premium"
    ):
        if "UserId" in data["Item"]:
            UserId = data["Item"]["UserId"]
            print(UserId)
            try:
                with initialize_postgresql() as conn:
                    with conn.cursor() as cur:
                        wallet_id = uuid4()
                        t_amount = getPricing(request.headers["X-Pricing"])
                        t_type = "Debit"
                        t_purpose = "API Usage"
                        last_updated_on = (
                            datetime.datetime.now().isoformat(timespec="milliseconds")
                            + "Z"
                        )

                        query = f"""
                        INSERT INTO wallet ("UserId", "WalletId", "TDate", "TAmount", "TType", "TPurpose", "LastUpdatedOn") 
                        VALUES ('{UserId}', '{wallet_id}', '{last_updated_on}', {t_amount}, '{t_type}', '{t_purpose}', '{last_updated_on}') 
                        RETURNING *;
                        """
                        cur.execute(query=query)
                        conn.commit()
                        return True
            except Exception as error:
                print(error)
                return False
    elif request.headers["X-Pricing"] == "Basic":
        FreeLimit = 1
        FreeDate = str(datetime.date.today())
        if "FreeLimit" in data["Item"] and "FreeDate" in data["Item"]:
            print(
                FreeDate, data["Item"]["FreeDate"], FreeDate == data["Item"]["FreeDate"]
            )
            if (
                int(data["Item"]["FreeLimit"]) >= 10
                and FreeDate == data["Item"]["FreeDate"]
            ):
                return False
            elif (
                int(data["Item"]["FreeLimit"]) < 10
                and FreeDate == data["Item"]["FreeDate"]
            ):
                FreeLimit = int(data["Item"]["FreeLimit"]) + 1
        table.update_item(
            Key={"key": request.headers["X-APIKey"]},
            UpdateExpression="set FreeLimit= :free, FreeDate= :freeDate",
            ExpressionAttributeValues={":free": FreeLimit, ":freeDate": FreeDate},
            ReturnValues="UPDATED_NEW",
        )
        return True
    else:
        return False
