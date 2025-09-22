import pytest
from backend.trading_manager import _decide_trade
from backend.database import TradingConfig, Balance

def test_decide_trade_profitable_spread():
    """
    Tests that a trade is correctly identified when the spread is profitable.
    """
    bids = [['100.0', '10']]
    asks = [['100.08', '10']] # 0.08% spread
    config = TradingConfig(is_active=True, demo_mode=False, max_capital=150.0)
    balance = Balance(total_balance=1000.0, available_balance=1000.0)

    trade_details = _decide_trade(bids, asks, config, balance)

    assert trade_details is not None
    assert trade_details['buy_price'] == 100.0
    assert trade_details['quantity'] > 0

def test_decide_trade_spread_too_small():
    """
    Tests that no trade is made when the spread is too small.
    """
    bids = [['100.0', '10']]
    asks = [['100.01', '10']] # 0.01% spread
    config = TradingConfig(is_active=True, demo_mode=False, max_capital=150.0)
    balance = Balance(total_balance=1000.0, available_balance=1000.0)

    trade_details = _decide_trade(bids, asks, config, balance)

    assert trade_details is None

def test_decide_trade_spread_too_large():
    """
    Tests that no trade is made when the spread is too large.
    """
    bids = [['100.0', '10']]
    asks = [['101.0', '10']] # 1.0% spread
    config = TradingConfig(is_active=True, demo_mode=False, max_capital=150.0)
    balance = Balance(total_balance=1000.0, available_balance=1000.0)

    trade_details = _decide_trade(bids, asks, config, balance)

    assert trade_details is None

def test_decide_trade_insufficient_capital():
    """
    Tests that no trade is made when the capital is insufficient.
    """
    bids = [['100.0', '10']]
    asks = [['100.08', '10']]
    # max_capital is too low, resulting in a trade < $10
    config = TradingConfig(is_active=True, demo_mode=False, max_capital=50.0)
    balance = Balance(total_balance=1000.0, available_balance=1000.0)

    trade_details = _decide_trade(bids, asks, config, balance)

    assert trade_details is None
