import React, { useState, useEffect } from 'react';
import './App.css';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Switch } from './components/ui/switch';
import { Badge } from './components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { toast } from 'sonner';
import axios from 'axios';
import { Toaster } from './components/ui/sonner';
import { 
  TrendingUp, 
  TrendingDown, 
  Play, 
  Square, 
  Settings, 
  Activity,
  DollarSign,
  BarChart3,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [tokens, setTokens] = useState([]);
  const [config, setConfig] = useState({
    max_capital: 65.1,
    profit_target_min: 0.08,
    profit_target_max: 0.10,
    max_operations_per_day: 3000,
    selected_token: '',
    is_active: false,
    demo_mode: true
  });
  const [balance, setBalance] = useState({
    total_balance: 65.1,
    available_balance: 65.1,
    in_orders: 0.0,
    total_profit_today: 0.0,
    operations_today: 0
  });
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = `${BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://')}/api/ws`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        console.log('WebSocket conectado');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'price_update') {
          setTokens(message.data);
        } else if (message.type === 'new_trade') {
          loadTrades();
          loadBalance();
          toast.success('Nueva operación ejecutada!');
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        console.log('WebSocket desconectado');
        // Intentar reconectar después de 3 segundos
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error('Error WebSocket:', error);
        setWsConnected(false);
      };
    };

    connectWebSocket();
  }, []);

  // Load initial data
  useEffect(() => {
    loadTokens();
    loadConfig();
    loadBalance();
    loadTrades();
  }, []);

  const loadTokens = async () => {
    try {
      const response = await axios.get(`${API}/tokens`);
      setTokens(response.data.tokens);
    } catch (error) {
      console.error('Error loading tokens:', error);
      toast.error('Error al cargar tokens');
    }
  };

  const loadConfig = async () => {
    try {
      const response = await axios.get(`${API}/config`);
      setConfig(response.data);
    } catch (error) {
      console.error('Error loading config:', error);
    }
  };

  const loadBalance = async () => {
    try {
      const response = await axios.get(`${API}/balance`);
      setBalance(response.data);
    } catch (error) {
      console.error('Error loading balance:', error);
    }
  };

  const loadTrades = async () => {
    try {
      const response = await axios.get(`${API}/trades?limit=20`);
      setTrades(response.data);
    } catch (error) {
      console.error('Error loading trades:', error);
    }
  };

  const updateConfig = async (updates) => {
    try {
      const response = await axios.post(`${API}/config`, updates);
      setConfig(response.data);
      toast.success('Configuración actualizada');
    } catch (error) {
      console.error('Error updating config:', error);
      toast.error('Error al actualizar configuración');
    }
  };

  const toggleTrading = async () => {
    try {
      setLoading(true);
      if (config.is_active) {
        await axios.post(`${API}/trading/stop`);
        toast.success('Trading detenido');
      } else {
        if (!config.selected_token) {
          toast.error('Selecciona un token primero');
          return;
        }
        await axios.post(`${API}/trading/start`);
        toast.success('Trading iniciado');
      }
      await loadConfig();
    } catch (error) {
      console.error('Error toggling trading:', error);
      toast.error('Error al cambiar estado del trading');
    } finally {
      setLoading(false);
    }
  };

  const simulateTrade = async () => {
    if (!config.selected_token) {
      toast.error('Selecciona un token primero');
      return;
    }
    
    try {
      setLoading(true);
      await axios.post(`${API}/trading/simulate`);
      // El WebSocket manejará las notificaciones
    } catch (error) {
      console.error('Error simulating trade:', error);
      toast.error('Error al simular operación');
    } finally {
      setLoading(false);
    }
  };

  const selectedTokenData = tokens.find(t => t.symbol === config.selected_token);

  return (
    <div className="min-h-screen bg-app text-white">
      <Toaster theme="dark" />
      
      {/* Header */}
      <header className="border-b border-gray-800 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-green-400 to-green-600 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-2xl font-bold">Binance Alpha Trader</h1>
            <Badge variant={config.demo_mode ? "secondary" : "destructive"} className="ml-2">
              {config.demo_mode ? "DEMO" : "LIVE"}
            </Badge>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm text-gray-400">
                {wsConnected ? 'Conectado' : 'Desconectado'}
              </span>
            </div>
            
            <Badge variant={config.is_active ? "default" : "secondary"} className="text-xs">
              {config.is_active ? 'ACTIVO' : 'INACTIVO'}
            </Badge>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Panel Principal */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="bg-gray-900 border-gray-800">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-2">
                    <DollarSign className="w-5 h-5 text-green-500" />
                    <div>
                      <p className="text-sm text-gray-400">Balance Total</p>
                      <p className="text-xl font-bold text-green-400">
                        ${balance.total_balance.toFixed(2)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-gray-900 border-gray-800">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-2">
                    <TrendingUp className="w-5 h-5 text-blue-500" />
                    <div>
                      <p className="text-sm text-gray-400">Ganancia Hoy</p>
                      <p className={`text-xl font-bold ${balance.total_profit_today >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${balance.total_profit_today.toFixed(4)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-gray-900 border-gray-800">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-2">
                    <Activity className="w-5 h-5 text-purple-500" />
                    <div>
                      <p className="text-sm text-gray-400">Operaciones</p>
                      <p className="text-xl font-bold">
                        {balance.operations_today}/{config.max_operations_per_day}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-gray-900 border-gray-800">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-2">
                    <Zap className="w-5 h-5 text-yellow-500" />
                    <div>
                      <p className="text-sm text-gray-400">Disponible</p>
                      <p className="text-xl font-bold text-blue-400">
                        ${balance.available_balance.toFixed(2)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Token Selection & Control */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="w-5 h-5" />
                  <span>Control de Trading</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="token-select">Token Seleccionado</Label>
                    <Select 
                      value={config.selected_token} 
                      onValueChange={(value) => updateConfig({ selected_token: value })}
                    >
                      <SelectTrigger className="bg-gray-800 border-gray-700">
                        <SelectValue placeholder="Seleccionar token" />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-800 border-gray-700">
                        {tokens.map((token) => (
                          <SelectItem key={token.symbol} value={token.symbol} className="text-white">
                            <div className="flex items-center justify-between w-full">
                              <span>{token.symbol}</span>
                              <div className="flex items-center space-x-2 ml-4">
                                <span className="text-sm">${token.price.toFixed(8)}</span>
                                <span className={`text-xs ${token.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {token.change >= 0 ? '+' : ''}{token.change.toFixed(2)}%
                                </span>
                              </div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {selectedTokenData && (
                      <div className="mt-2 p-2 bg-gray-800 rounded-lg">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-400">Precio actual:</span>
                          <span className="font-mono">${selectedTokenData.price.toFixed(8)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-400">Cambio 24h:</span>
                          <span className={`font-mono ${selectedTokenData.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {selectedTokenData.change >= 0 ? '+' : ''}{selectedTokenData.change.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-center space-x-4">
                      <Button
                        onClick={toggleTrading}
                        disabled={loading || !config.selected_token}
                        size="lg"
                        className={`w-full ${
                          config.is_active 
                            ? 'bg-red-600 hover:bg-red-700 text-white' 
                            : 'bg-green-600 hover:bg-green-700 text-white'
                        }`}
                      >
                        {config.is_active ? (
                          <>
                            <Square className="w-5 h-5 mr-2" />
                            DETENER TRADING
                          </>
                        ) : (
                          <>
                            <Play className="w-5 h-5 mr-2" />
                            INICIAR TRADING
                          </>
                        )}
                      </Button>
                    </div>
                    
                    <Button
                      onClick={simulateTrade}
                      disabled={loading || !config.selected_token}
                      variant="outline"
                      className="w-full border-blue-600 text-blue-400 hover:bg-blue-600 hover:text-white"
                    >
                      <Zap className="w-4 h-4 mr-2" />
                      Simular Operación
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Trades */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="w-5 h-5" />
                  <span>Operaciones Recientes</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-gray-800">
                        <TableHead className="text-gray-400">Hora</TableHead>
                        <TableHead className="text-gray-400">Par</TableHead>
                        <TableHead className="text-gray-400">Lado</TableHead>
                        <TableHead className="text-gray-400">Cantidad</TableHead>
                        <TableHead className="text-gray-400">Precio</TableHead>
                        <TableHead className="text-gray-400">Ganancia</TableHead>
                        <TableHead className="text-gray-400">Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {trades.slice(0, 10).map((trade) => (
                        <TableRow key={trade.id} className="border-gray-800">
                          <TableCell className="text-gray-300">
                            {new Date(trade.timestamp).toLocaleTimeString()}
                          </TableCell>
                          <TableCell className="font-mono">{trade.symbol}</TableCell>
                          <TableCell>
                            <Badge 
                              variant={trade.side === 'BUY' ? 'default' : 'secondary'}
                              className={trade.side === 'BUY' ? 'bg-green-600' : 'bg-red-600'}
                            >
                              {trade.side}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono">{trade.quantity.toFixed(8)}</TableCell>
                          <TableCell className="font-mono">${trade.price.toFixed(8)}</TableCell>
                          <TableCell className={`font-mono ${trade.profit > 0 ? 'text-green-400' : trade.profit < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                            {trade.profit > 0 ? '+' : ''}${trade.profit.toFixed(6)}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-1">
                              {trade.status === 'COMPLETED' ? (
                                <CheckCircle className="w-4 h-4 text-green-500" />
                              ) : trade.status === 'PENDING' ? (
                                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                              ) : (
                                <XCircle className="w-4 h-4 text-red-500" />
                              )}
                              <span className="text-xs">{trade.status}</span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Panel de Configuración */}
          <div className="space-y-6">
            
            {/* Configuration */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="w-5 h-5" />
                  <span>Configuración</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="max-capital">Capital Máximo (USD)</Label>
                  <Input
                    id="max-capital"
                    type="number"
                    max="200.0"
                    step="1.0"
                    value={config.max_capital}
                    onChange={(e) => updateConfig({ max_capital: parseFloat(e.target.value) })}
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">Máximo: $200.00</p>
                </div>

                <div>
                  <Label htmlFor="profit-min">Ganancia Mínima (%)</Label>
                  <Input
                    id="profit-min"
                    type="number"
                    step="0.1"
                    min="0.0"
                    max="0.8"
                    value={config.profit_target_min}
                    onChange={(e) => updateConfig({ profit_target_min: parseFloat(e.target.value) })}
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>

                <div>
                  <Label htmlFor="profit-max">Ganancia Máxima (%)</Label>
                  <Input
                    id="profit-max"
                    type="number"
                    step="0.1"
                    min="0.0"
                    max="0.8"
                    value={config.profit_target_max}
                    onChange={(e) => updateConfig({ profit_target_max: parseFloat(e.target.value) })}
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>

                <div>
                  <Label htmlFor="max-ops">Máx. Operaciones/Día</Label>
                  <Input
                    id="max-ops"
                    type="number"
                    max="3000"
                    value={config.max_operations_per_day}
                    onChange={(e) => updateConfig({ max_operations_per_day: parseInt(e.target.value) })}
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">Máximo: 3000</p>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="demo-mode"
                    checked={config.demo_mode}
                    onCheckedChange={(checked) => updateConfig({ demo_mode: checked })}
                  />
                  <Label htmlFor="demo-mode">Modo Demo</Label>
                </div>
              </CardContent>
            </Card>

            {/* Market Overview */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="w-5 h-5" />
                  <span>Tokens Alpha</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 max-h-96 overflow-y-auto">
                {tokens.map((token) => (
                  <div 
                    key={token.symbol} 
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      config.selected_token === token.symbol 
                        ? 'bg-blue-900 border-blue-600' 
                        : 'bg-gray-800 border-gray-700 hover:bg-gray-700'
                    }`}
                    onClick={() => updateConfig({ selected_token: token.symbol })}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm">{token.symbol}</span>
                      <div className="flex items-center space-x-1">
                        {token.change >= 0 ? (
                          <TrendingUp className="w-3 h-3 text-green-400" />
                        ) : (
                          <TrendingDown className="w-3 h-3 text-red-400" />
                        )}
                        <span className={`text-xs ${token.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {token.change >= 0 ? '+' : ''}{token.change.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-gray-400">${token.price.toFixed(8)}</span>
                      <span className="text-xs text-gray-500">Vol: {(token.volume / 1000000).toFixed(1)}M</span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;