from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from typing import List
from datetime import datetime, timezone, timedelta
import asyncio
import random
import json

from backend.database import (
    db,
    close_mongo_connection,
    TradingConfig,
    TradingConfigUpdate,
    Trade,
    Balance,
)
from backend.binance_client import get_binance_client, close_binance_client, get_all_tickers
from backend.trading_manager import start_trading_session, stop_trading_session, stop_all_sessions

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Store for active WebSocket connections
active_connections: List[WebSocket] = []

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

# Cache for token data
token_cache = {"data": None, "last_updated": None}
CACHE_DURATION = timedelta(seconds=10)

@api_router.get("/tokens")
async def get_alpha_tokens():
    """Get list of Alpha tokens with updated prices from Binance"""
    now = datetime.now(timezone.utc)

    # Use cache if it's recent
    if token_cache["last_updated"] and (now - token_cache["last_updated"]) < CACHE_DURATION:
        return {"tokens": token_cache["data"]}

    # Fetch 24h ticker data from Binance
    # The get_all_tickers function actually fetches 24h ticker data
    tickers = await get_all_tickers()
    if not tickers:
        raise HTTPException(status_code=503, detail="Could not fetch token data from Binance")

    # Filter for USDT pairs and format for the frontend
    alpha_tokens = []
    for ticker in tickers:
        if ticker['symbol'].endswith('USDT'):
            try:
                # The frontend expects symbol with a slash, e.g., BTC/USDT
                formatted_symbol = f"{ticker['symbol'][:-4]}/{ticker['symbol'][-4:]}"

                alpha_tokens.append({
                    "symbol": formatted_symbol,
                    "price": float(ticker['lastPrice']),
                    "change": float(ticker['priceChangePercent']),
                    "volume": float(ticker['quoteVolume'])
                })
            except (KeyError, ValueError) as e:
                # Log if a ticker has missing data, but don't crash
                logger.warning(f"Could not process ticker {ticker.get('symbol', 'N/A')}: {e}")
                continue
    
    # Sort by volume to get the "Alpha" tokens
    alpha_tokens.sort(key=lambda x: x['volume'], reverse=True)

    # Update cache
    token_cache["data"] = alpha_tokens
    token_cache["last_updated"] = now

    return {"tokens": alpha_tokens}

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
    """Start automatic trading"""
    config_data = await db.trading_configs.find_one({}, sort=[("created_at", -1)])
    if not config_data:
        raise HTTPException(status_code=404, detail="Configuration not found")

    config = TradingConfig(**config_data)
    
    if not config.selected_token:
        raise HTTPException(status_code=400, detail="Token not selected")

    await db.trading_configs.update_one(
        {"id": config.id},
        {"$set": {"is_active": True}}
    )
    
    # Start the trading session in the background, passing the notifier and db
    await start_trading_session(config.selected_token, notify_clients, db)

    return {"message": "Trading started", "status": "active"}

@api_router.post("/trading/stop")
async def stop_trading():
    """Stop automatic trading"""
    config_data = await db.trading_configs.find_one({}, sort=[("created_at", -1)])
    if not config_data:
        raise HTTPException(status_code=404, detail="Configuration not found")

    config = TradingConfig(**config_data)
    
    await db.trading_configs.update_one(
        {"id": config.id},
        {"$set": {"is_active": False}}
    )
    
    # Stop the trading session
    if config.selected_token:
        await stop_trading_session(config.selected_token)

    return {"message": "Trading stopped", "status": "inactive"}

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

# WebSocket for real-time updates
@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Send price updates every 5 seconds
            await asyncio.sleep(5)
            
            # Fetch the latest token data (uses the cache)
            token_data = await get_alpha_tokens()
            
            await notify_clients({
                "type": "price_update",
                "data": token_data["tokens"]
            })
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"Error in websocket endpoint: {e}")
        if websocket in active_connections:
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

@app.on_event("startup")
async def startup_event():
    # Initialize Binance client on startup
    await get_binance_client()

@app.on_event("shutdown")
async def shutdown_event():
    # Stop all trading sessions
    await stop_all_sessions()
    # Close MongoDB client
    close_mongo_connection()
    # Close Binance client
    await close_binance_client()