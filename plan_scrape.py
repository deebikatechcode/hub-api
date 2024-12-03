from boto3.dynamodb.conditions import Key
from db import initialize_db
from fastapi import HTTPException
from pydantic import BaseModel
class PlanResponse(BaseModel):
    PlanId: str
    ProviderId: str
    Price: float
    PlanDetails: str
    createdAt: str
ddb = initialize_db()
recharge_plan_table = ddb.Table('Recharge_Plans')

async def fetch_plans_by_provider(provider_id: str):
    """
    Fetch plans from DynamoDB based on provider_id.
    """
    try:
        plans_response = recharge_plan_table.query(
            IndexName='ProviderIdIndex',
            KeyConditionExpression=Key('ProviderId').eq(provider_id)
        )
        plans = plans_response.get('Items', [])
        
        if not plans:
            raise HTTPException(status_code=404, detail="No plans found for this provider.")
        
        return plans

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching plans: {str(e)}")
