import os
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Connection
mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(mongo_url)
db = client[os.getenv("DB_NAME", "trading_platform")]

def close_mongo_connection():
    client.close()

# Pydantic Models
class TradingConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    max_capital: float = Field(default=150.0, le=200.0)
    profit_target_min: float = Field(default=0.08, ge=0.0, le=0.8)
    profit_target_max: float = Field(default=0.10, ge=0.0, le=0.8)
    max_operations_per_day: int = Field(default=3000, le=3000)
    selected_token: str = ""
    is_active: bool = False
    demo_mode: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TradingConfigUpdate(BaseModel):
    max_capital: Optional[float] = Field(None, le=200.0)
    profit_target_min: Optional[float] = Field(None, ge=0.0, le=0.8)
    profit_target_max: Optional[float] = Field(None, ge=0.0, le=0.8)
    max_operations_per_day: Optional[int] = Field(None, le=3000)
    selected_token: Optional[str] = None
    is_active: Optional[bool] = None
    demo_mode: Optional[bool] = None

class Trade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    price: float
    profit: float = 0.0
    status: str = "COMPLETED"  # COMPLETED, PENDING, CANCELLED
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    demo: bool = True

class Balance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_balance: float
    available_balance: float
    in_orders: float = 0.0
    total_profit_today: float = 0.0
    operations_today: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
