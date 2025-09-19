import requests
import sys
import json
import time
from datetime import datetime

class BinanceAlphaTradingTester:
    def __init__(self, base_url="https://binance-trader-25.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_get_tokens(self):
        """Test getting Alpha tokens list"""
        success, response = self.run_test("Get Alpha Tokens", "GET", "tokens", 200)
        if success and 'tokens' in response:
            tokens = response['tokens']
            print(f"   Found {len(tokens)} tokens")
            if len(tokens) > 0:
                print(f"   Sample token: {tokens[0]['symbol']} - ${tokens[0]['price']}")
            return True, tokens
        return False, []

    def test_get_config(self):
        """Test getting trading configuration"""
        success, response = self.run_test("Get Trading Config", "GET", "config", 200)
        if success:
            print(f"   Max Capital: ${response.get('max_capital', 'N/A')}")
            print(f"   Profit Target: {response.get('profit_target_min', 'N/A')}% - {response.get('profit_target_max', 'N/A')}%")
            print(f"   Selected Token: {response.get('selected_token', 'None')}")
            print(f"   Demo Mode: {response.get('demo_mode', 'N/A')}")
            return True, response
        return False, {}

    def test_update_config(self):
        """Test updating trading configuration"""
        config_data = {
            "max_capital": 50.0,
            "profit_target_min": 0.08,
            "profit_target_max": 0.10,
            "selected_token": "AIOZ/USDT",
            "demo_mode": True
        }
        success, response = self.run_test("Update Trading Config", "POST", "config", 200, config_data)
        if success:
            print(f"   Updated Max Capital: ${response.get('max_capital', 'N/A')}")
            print(f"   Updated Selected Token: {response.get('selected_token', 'None')}")
            return True, response
        return False, {}

    def test_get_balance(self):
        """Test getting current balance"""
        success, response = self.run_test("Get Balance", "GET", "balance", 200)
        if success:
            print(f"   Total Balance: ${response.get('total_balance', 'N/A')}")
            print(f"   Available Balance: ${response.get('available_balance', 'N/A')}")
            print(f"   Today's Profit: ${response.get('total_profit_today', 'N/A')}")
            print(f"   Operations Today: {response.get('operations_today', 'N/A')}")
            return True, response
        return False, {}

    def test_simulate_trade(self):
        """Test trade simulation"""
        # First ensure we have a token selected
        self.test_update_config()
        
        success, response = self.run_test("Simulate Trade", "POST", "trading/simulate", 200)
        if success:
            print(f"   Buy Trade: {response.get('buy_trade', {}).get('symbol', 'N/A')} at ${response.get('buy_trade', {}).get('price', 'N/A')}")
            print(f"   Sell Trade: {response.get('sell_trade', {}).get('symbol', 'N/A')} at ${response.get('sell_trade', {}).get('price', 'N/A')}")
            print(f"   Profit: ${response.get('profit', 'N/A')}")
            return True, response
        return False, {}

    def test_get_trades(self):
        """Test getting trade history"""
        success, response = self.run_test("Get Trade History", "GET", "trades?limit=10", 200)
        if success and isinstance(response, list):
            print(f"   Found {len(response)} trades")
            if len(response) > 0:
                latest_trade = response[0]
                print(f"   Latest trade: {latest_trade.get('symbol', 'N/A')} {latest_trade.get('side', 'N/A')} - ${latest_trade.get('price', 'N/A')}")
            return True, response
        return False, []

    def test_trading_start_stop(self):
        """Test starting and stopping trading"""
        # Test start trading
        start_success, start_response = self.run_test("Start Trading", "POST", "trading/start", 200)
        
        # Test stop trading
        stop_success, stop_response = self.run_test("Stop Trading", "POST", "trading/stop", 200)
        
        return start_success and stop_success

    def test_websocket_connection(self):
        """Test WebSocket connection (basic connectivity test)"""
        try:
            import websocket
            ws_url = f"{self.base_url.replace('https://', 'wss://').replace('http://', 'ws://')}/api/ws"
            print(f"\n🔍 Testing WebSocket Connection...")
            print(f"   URL: {ws_url}")
            
            # Simple connection test
            ws = websocket.create_connection(ws_url, timeout=5)
            ws.close()
            print("✅ WebSocket connection successful")
            self.tests_run += 1
            self.tests_passed += 1
            return True
        except Exception as e:
            print(f"❌ WebSocket connection failed: {str(e)}")
            self.tests_run += 1
            return False

def main():
    print("🚀 Starting Binance Alpha Trading Platform API Tests")
    print("=" * 60)
    
    tester = BinanceAlphaTradingTester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Get Tokens", tester.test_get_tokens),
        ("Get Config", tester.test_get_config),
        ("Update Config", tester.test_update_config),
        ("Get Balance", tester.test_get_balance),
        ("Simulate Trade", tester.test_simulate_trade),
        ("Get Trades", tester.test_get_trades),
        ("Trading Start/Stop", tester.test_trading_start_stop),
        ("WebSocket Connection", tester.test_websocket_connection),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if not result:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            failed_tests.append(test_name)
            tester.tests_run += 1
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"   - {test}")
    else:
        print(f"\n✅ All tests passed!")
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())