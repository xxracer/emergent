import os
from dotenv import load_dotenv
from binance import AsyncClient

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

# It's recommended to create a single instance of the client and reuse it
# The client will be initialized when this module is first imported.
binance_client = None

async def get_binance_client():
    """
    Initializes and returns an asynchronous Binance client.
    Uses a singleton pattern to ensure only one client is created.
    """
    global binance_client
    if binance_client is None:
        # For security, it's better to handle the case where keys are not set
        if not api_key or not api_secret:
            # In a real app, you might want to raise an exception or log a critical error
            print("CRITICAL: Binance API Key/Secret not found in .env file.")
            # Returning None or raising an exception would be appropriate here.
            # For now, we'll allow it to fail during client creation.
            pass

        print("Initializing Binance client...")
        binance_client = await AsyncClient.create(api_key, api_secret)

        # Check if we should use the testnet
        # This can be controlled by another environment variable, e.g., USE_TESTNET=true
        if os.getenv("USE_TESTNET", "false").lower() == "true":
            print("Using Binance Testnet")
            binance_client.API_URL = 'https://testnet.binance.vision/api'

    return binance_client

async def close_binance_client():
    """Closes the Binance client connection if it exists."""
    global binance_client
    if binance_client:
        await binance_client.close_connection()
        binance_client = None
        print("Binance client connection closed.")

async def get_server_time():
    """
    Fetches the current server time from Binance.
    A good way to test the API connection.
    """
    client = await get_binance_client()
    if not client:
        return None
    try:
        time_res = await client.get_server_time()
        return time_res["serverTime"]
    except Exception as e:
        print(f"Error connecting to Binance: {e}")
        return None

async def get_all_tickers():
    """
    Fetches the latest price for all symbols.
    """
    client = await get_binance_client()
    if not client:
        return []
    try:
        # This actually gets the 24h ticker price change statistics
        tickers = await client.get_ticker()
        return tickers
    except Exception as e:
        print(f"Error fetching all tickers: {e}")
        return []

async def create_test_order(symbol, side, type, quantity, price, timeInForce='GTC'):
    """
    Creates a test order.
    """
    client = await get_binance_client()
    if not client:
        return None
    try:
        order = await client.create_test_order(
            symbol=symbol,
            side=side,
            type=type,
            timeInForce=timeInForce,
            quantity=quantity,
            price=price
        )
        return order
    except Exception as e:
        print(f"Error creating test order for {symbol}: {e}")
        return None

async def create_order(symbol, side, type, quantity, price, timeInForce='GTC'):
    """
    Creates a real order.
    """
    client = await get_binance_client()
    if not client:
        return None
    try:
        order = await client.create_order(
            symbol=symbol,
            side=side,
            type=type,
            timeInForce=timeInForce,
            quantity=quantity,
            price=price
        )
        return order
    except Exception as e:
        print(f"Error creating order for {symbol}: {e}")
        return None

# Example of how to use it (optional, for direct testing of this module)
if __name__ == "__main__":
    import asyncio

    async def test_connection():
        print("Testing Binance API connection...")
        server_time = await get_server_time()
        if server_time:
            from datetime import datetime
            print(f"Successfully connected to Binance. Server time: {datetime.fromtimestamp(server_time / 1000)}")
        else:
            print("Failed to connect to Binance.")

        await close_binance_client()

    asyncio.run(test_connection())
