from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str


@api_router.get("/")
async def root():
    return {"message": "DaoChain Dashboard API"}


@api_router.get("/dashboard/stats")
async def get_dashboard_stats():
    return {
        "active_nodes": 1284,
        "total_deployments": 847,
        "smart_contracts": 312,
        "network_latency": "12ms",
        "node_change": 5.2,
        "deployment_change": 12.8,
        "contract_change": -2.1,
        "latency_change": -8.4,
    }


@api_router.get("/dashboard/logs")
async def get_dashboard_logs():
    return [
        {"id": "0x7a3f...c8d1", "contract": "GovernanceDAO.sol", "action": "Deploy", "status": "Success", "gas": "0.0042 ETH", "timestamp": "2 min ago", "block": "#18,294,721"},
        {"id": "0x1b4e...a9f2", "contract": "TokenVault.sol", "action": "Upgrade", "status": "Success", "gas": "0.0031 ETH", "timestamp": "8 min ago", "block": "#18,294,718"},
        {"id": "0x9c2d...b7e3", "contract": "StakingPool.sol", "action": "Deploy", "status": "Pending", "gas": "0.0058 ETH", "timestamp": "15 min ago", "block": "#18,294,715"},
        {"id": "0x4d8a...f1c4", "contract": "NFTMarket.sol", "action": "Verify", "status": "Failed", "gas": "0.0019 ETH", "timestamp": "23 min ago", "block": "#18,294,710"},
        {"id": "0x6e5f...d2a5", "contract": "BridgeProxy.sol", "action": "Deploy", "status": "Success", "gas": "0.0067 ETH", "timestamp": "31 min ago", "block": "#18,294,706"},
        {"id": "0x3c1b...e8f6", "contract": "OracleAdapter.sol", "action": "Deploy", "status": "Success", "gas": "0.0044 ETH", "timestamp": "45 min ago", "block": "#18,294,699"},
        {"id": "0x8f2a...c3d7", "contract": "MultiSigWallet.sol", "action": "Upgrade", "status": "Pending", "gas": "0.0052 ETH", "timestamp": "1 hr ago", "block": "#18,294,690"},
    ]


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
