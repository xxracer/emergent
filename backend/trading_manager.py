import asyncio
import logging
from typing import Dict, Callable, Optional, List, Tuple
from backend.binance_client import get_binance_client, create_test_order, create_order
from binance import DepthCacheManager
from backend.database import db, Trade, Balance, TradingConfig

logger = logging.getLogger(__name__)

active_trading_sessions: Dict[str, asyncio.Task] = {}

def _decide_trade(
    bids: List[List[str]],
    asks: List[List[str]],
    config: TradingConfig,
    balance: Balance
) -> Optional[Dict]:
    """
    Core logic to decide if a trade should be made.
    This is a synchronous function for easy testing.
    Returns a dictionary with trade details or None.
    """
    if not bids or not asks:
        return None

    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])

    spread = round(((best_ask - best_bid) / best_bid) * 100, 8)
    print(f"Calculated spread: {spread}, Target: {config.profit_target_min}-{config.profit_target_max}")

    if not (config.profit_target_min <= spread <= config.profit_target_max):
        return None

    logger.info(f"Profitable spread detected: {spread:.4f}%")

    trade_amount_usd = min(config.max_capital * 0.1, balance.available_balance * 0.05)

    if trade_amount_usd < 10:
        logger.warning(f"Insufficient capital to trade. Needed > $10, have ${trade_amount_usd:.2f}")
        return None

    quantity = trade_amount_usd / best_bid
    sell_price = best_bid * (1 + (config.profit_target_min / 100))

    return {
        "quantity": quantity,
        "buy_price": best_bid,
        "sell_price": sell_price,
    }

async def _trade_loop(symbol: str, notifier: Callable, db):
    """
    The main loop for a single trading session.
    Connects to the depth stream and processes messages.
    """
    client = await get_binance_client()
    if not client:
        logger.error(f"Could not get Binance client for {symbol}. Stopping loop.")
        return

    logger.info(f"Starting trade loop for {symbol}...")

    async with DepthCacheManager(client, symbol=symbol) as dcm:
        while True:
            try:
                await dcm.wait_for_update()

                config_data = await db.trading_configs.find_one({}, sort=[("created_at", -1)])
                if not config_data:
                    logger.warning(f"[{symbol}] No trading config found. Skipping trade.")
                    await asyncio.sleep(5)
                    continue

                config = TradingConfig(**config_data)
                if not config.is_active:
                    logger.info(f"[{symbol}] Trading is inactive. Stopping trade loop.")
                    break

                balance_data = await db.balances.find_one({}, sort=[("timestamp", -1)])
                balance = Balance(**balance_data)

                bids = dcm.get_bids()
                asks = dcm.get_asks()

                trade_details = _decide_trade(bids, asks, config, balance)

                if trade_details:
                    quantity = trade_details["quantity"]
                    buy_price = trade_details["buy_price"]
                    sell_price = trade_details["sell_price"]

                    order_func = create_test_order if config.demo_mode else create_order

                    logger.info(f"[{symbol}] Executing {'TEST ' if config.demo_mode else ''}BUY order: {quantity:.8f} at ${buy_price:.8f}")
                    buy_order = await order_func(
                        symbol=symbol, side='BUY', type='LIMIT', timeInForce='GTC',
                        quantity=f"{quantity:.8f}", price=f"{buy_price:.8f}"
                    )

                    if not config.demo_mode and not buy_order:
                        logger.error(f"[{symbol}] Live BUY order failed. Aborting sell order.")
                        continue

                    logger.info(f"[{symbol}] Executing {'TEST ' if config.demo_mode else ''}SELL order: {quantity:.8f} at ${sell_price:.8f}")
                    sell_order = await order_func(
                        symbol=symbol, side='SELL', type='LIMIT', timeInForce='GTC',
                        quantity=f"{quantity:.8f}", price=f"{sell_price:.8f}"
                    )

                    profit = (sell_price - buy_price) * quantity

                    buy_trade = Trade(symbol=symbol.replace('USDT', '/USDT'), side="BUY", quantity=quantity, price=buy_price, demo=config.demo_mode)
                    sell_trade = Trade(symbol=symbol.replace('USDT', '/USDT'), side="SELL", quantity=quantity, price=sell_price, profit=profit, demo=config.demo_mode)
                    await db.trades.insert_many([buy_trade.model_dump(), sell_trade.model_dump()])

                    new_balance_val = balance.available_balance + profit
                    balance_update = Balance(
                        total_balance=new_balance_val,
                        available_balance=new_balance_val,
                        total_profit_today=balance.total_profit_today + profit,
                        operations_today=balance.operations_today + 1
                    )
                    await db.balances.insert_one(balance_update.model_dump())

                    await notifier({"type": "new_trade", "data": {"buy_trade": buy_trade.model_dump(), "sell_trade": sell_trade.model_dump()}})
                    await notifier({"type": "balance_update", "data": balance_update.model_dump()})

                    logger.info(f"[{symbol}] Trade completed. Profit: ${profit:.6f}")
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                logger.info(f"Trade loop for {symbol} cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in trade loop for {symbol}: {e}", exc_info=True)
                await asyncio.sleep(5)

    logger.info(f"Trade loop for {symbol} has stopped.")

async def start_trading_session(symbol: str, notifier: Callable, db):
    """
    Starts a new trading session for a given symbol if not already running.
    """
    normalized_symbol = symbol.replace('/', '')

    if normalized_symbol in active_trading_sessions:
        logger.warning(f"Trading session for {normalized_symbol} is already active.")
        return

    logger.info(f"Creating trading session for {normalized_symbol}...")

    task = asyncio.create_task(_trade_loop(normalized_symbol, notifier, db))
    active_trading_sessions[normalized_symbol] = task

    logger.info(f"Trading session for {normalized_symbol} started.")

async def stop_trading_session(symbol: str):
    """
    Stops an active trading session for a given symbol.
    """
    normalized_symbol = symbol.replace('/', '')

    if normalized_symbol not in active_trading_sessions:
        logger.warning(f"No active trading session found for {normalized_symbol}.")
        return

    logger.info(f"Stopping trading session for {normalized_symbol}...")

    task = active_trading_sessions[normalized_symbol]
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    del active_trading_sessions[normalized_symbol]
    logger.info(f"Trading session for {normalized_symbol} stopped.")

async def stop_all_sessions():
    """Stops all active trading sessions."""
    logger.info("Stopping all trading sessions...")
    symbols = list(active_trading_sessions.keys())
    for symbol in symbols:
        await stop_trading_session(symbol)
    logger.info("All trading sessions stopped.")
