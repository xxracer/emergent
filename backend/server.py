from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import asyncio
import random
import json

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

# Demo data - Simulación de tokens Alpha de Binance
DEMO_ALPHA_TOKENS = [
    {"symbol": "AIOZ/USDT", "price": 0.0847, "change": 12.5, "volume": 2850000},
    {"symbol": "SUPER/USDT", "price": 1.2340, "change": -3.2, "volume": 1420000},
    {"symbol": "JASMY/USDT", "price": 0.02156, "change": 8.7, "volume": 890000},
    {"symbol": "REEF/USDT", "price": 0.001823, "change": 15.3, "volume": 5600000},
    {"symbol": "AKRO/USDT", "price": 0.004567, "change": -1.8, "volume": 3200000},
    {"symbol": "ALPACA/USDT", "price": 0.1847, "change": 6.4, "volume": 720000},
    {"symbol": "DENT/USDT", "price": 0.001234, "change": 4.2, "volume": 8900000},
    {"symbol": "KEY/USDT", "price": 0.003456, "change": -7.1, "volume": 4500000},
]

# Store for active WebSocket connections
active_connections: List[WebSocket] = []

# Models
class TradingConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    max_capital: float = Field(default=65.1, le=65.1)
    profit_target_min: float = Field(default=0.08, ge=0.05, le=0.15)
    profit_target_max: float = Field(default=0.10, ge=0.05, le=0.15)
    max_operations_per_day: int = Field(default=3000, le=3000)
    selected_token: str = ""
    is_active: bool = False
    demo_mode: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TradingConfigUpdate(BaseModel):
    max_capital: Optional[float] = Field(None, le=65.1)
    profit_target_min: Optional[float] = Field(None, ge=0.05, le=0.15)
    profit_target_max: Optional[float] = Field(None, ge=0.05, le=0.15)
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

# Demo trading simulation
class DemoTrader:
    def __init__(self):
        self.balance = 65.1
        self.daily_operations = 0
        self.daily_profit = 0.0
        
    async def simulate_trade(self, symbol: str, config: TradingConfig):
        if self.daily_operations >= config.max_operations_per_day:
            return None
            
        # Simular precio de entrada y salida
        token_data = next((t for t in DEMO_ALPHA_TOKENS if t["symbol"] == symbol), None)
        if not token_data:
            return None
            
        entry_price = token_data["price"]
        profit_percent = random.uniform(config.profit_target_min, config.profit_target_max)
        exit_price = entry_price * (1 + profit_percent / 100)
        
        # Calcular cantidad basada en el capital disponible
        trade_amount = min(config.max_capital * 0.1, self.balance * 0.05)  # 10% del capital máximo o 5% del balance
        quantity = trade_amount / entry_price
        
        profit = quantity * (exit_price - entry_price)
        
        # Crear trades de compra y venta
        buy_trade = Trade(
            symbol=symbol,
            side="BUY",
            quantity=quantity,
            price=entry_price,
            profit=0.0,
            demo=True
        )
        
        sell_trade = Trade(
            symbol=symbol,
            side="SELL",
            quantity=quantity,
            price=exit_price,
            profit=profit,
            demo=True
        )
        
        # Actualizar balance y estadísticas
        self.balance += profit
        self.daily_operations += 1
        self.daily_profit += profit
        
        # Guardar en base de datos
        await db.trades.insert_one(buy_trade.dict())
        await db.trades.insert_one(sell_trade.dict())
        
        # Actualizar balance en DB
        balance_record = Balance(
            total_balance=self.balance,
            available_balance=self.balance,
            total_profit_today=self.daily_profit,
            operations_today=self.daily_operations
        )
        await db.balances.insert_one(balance_record.dict())
        
        return {"buy_trade": buy_trade, "sell_trade": sell_trade, "profit": profit}

demo_trader = DemoTrader()

# Routes
@api_router.get("/")
async def root():
    return {"message": "Binance Trading Platform API"}

@api_router.get("/tokens")
async def get_alpha_tokens():
    """Obtener lista de tokens Alpha con precios actualizados"""
    # En modo demo, devolver datos simulados
    # En modo real, esto se conectaría a la API de Binance
    for token in DEMO_ALPHA_TOKENS:
        # Simular pequeñas variaciones de precio
        price_change = random.uniform(-0.05, 0.05)
        token["price"] = round(token["price"] * (1 + price_change), 8)
        token["change"] = round(random.uniform(-10, 15), 2)
    
    return {"tokens": DEMO_ALPHA_TOKENS}

@api_router.post("/config", response_model=TradingConfig)
async def create_or_update_config(config_data: TradingConfigUpdate):
    """Crear o actualizar configuración de trading"""
    # Buscar configuración existente
    existing_config = await db.trading_configs.find_one({}, sort=[("created_at", -1)])
    
    if existing_config:
        # Actualizar configuración existente
        update_data = {k: v for k, v in config_data.dict().items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        await db.trading_configs.update_one(
            {"id": existing_config["id"]}, 
            {"$set": update_data}
        )
        
        # Obtener configuración actualizada
        updated_config = await db.trading_configs.find_one({"id": existing_config["id"]})
        return TradingConfig(**updated_config)
    else:
        # Crear nueva configuración
        config_dict = config_data.dict()
        config_dict = {k: v for k, v in config_dict.items() if v is not None}
        new_config = TradingConfig(**config_dict)
        
        await db.trading_configs.insert_one(new_config.dict())
        return new_config

@api_router.get("/config", response_model=TradingConfig)
async def get_config():
    """Obtener configuración actual"""
    config = await db.trading_configs.find_one({}, sort=[("created_at", -1)])
    if not config:
        # Crear configuración por defecto
        default_config = TradingConfig()
        await db.trading_configs.insert_one(default_config.dict())
        return default_config
    return TradingConfig(**config)

@api_router.post("/trading/start")
async def start_trading():
    """Iniciar trading automático"""
    config = await db.trading_configs.find_one({}, sort=[("created_at", -1)])
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    await db.trading_configs.update_one(
        {"id": config["id"]},
        {"$set": {"is_active": True}}
    )
    
    return {"message": "Trading iniciado", "status": "active"}

@api_router.post("/trading/stop")
async def stop_trading():
    """Detener trading automático"""
    config = await db.trading_configs.find_one({}, sort=[("created_at", -1)])
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    await db.trading_configs.update_one(
        {"id": config["id"]},
        {"$set": {"is_active": False}}
    )
    
    return {"message": "Trading detenido", "status": "inactive"}

@api_router.post("/trading/simulate")
async def simulate_trade_operation():
    """Simular una operación de trading para demostración"""
    config = await db.trading_configs.find_one({}, sort=[("created_at", -1)])
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    config_obj = TradingConfig(**config)
    
    if not config_obj.selected_token:
        raise HTTPException(status_code=400, detail="Token no seleccionado")
    
    result = await demo_trader.simulate_trade(config_obj.selected_token, config_obj)
    
    if not result:
        raise HTTPException(status_code=400, detail="No se pudo simular la operación")
    
    # Notificar a clientes WebSocket
    await notify_clients({
        "type": "new_trade",
        "data": result
    })
    
    return result

@api_router.get("/trades", response_model=List[Trade])
async def get_trades(limit: int = 50):
    """Obtener historial de trades"""
    trades = await db.trades.find().sort("timestamp", -1).limit(limit).to_list(limit)
    return [Trade(**trade) for trade in trades]

@api_router.get("/balance", response_model=Balance)
async def get_balance():
    """Obtener balance actual"""
    balance = await db.balances.find_one({}, sort=[("timestamp", -1)])
    if not balance:
        default_balance = Balance(
            total_balance=65.1,
            available_balance=65.1
        )
        await db.balances.insert_one(default_balance.dict())
        return default_balance
    return Balance(**balance)

# WebSocket para actualizaciones en tiempo real
@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Enviar actualizaciones de precios cada 2 segundos
            await asyncio.sleep(2)
            
            # Simular actualización de precios
            for token in DEMO_ALPHA_TOKENS:
                price_change = random.uniform(-0.01, 0.01)
                token["price"] = round(token["price"] * (1 + price_change), 8)
            
            await websocket.send_text(json.dumps({
                "type": "price_update",
                "data": DEMO_ALPHA_TOKENS
            }))
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def notify_clients(message: dict):
    """Notificar a todos los clientes WebSocket conectados"""
    if active_connections:
        for connection in active_connections.copy():
            try:
                await connection.send_text(json.dumps(message))
            except:
                active_connections.remove(connection)

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