# AxiomTrade Multi-Purpose Trading Bot

A free and open-source trading bot built on the AxiomTrade API with comprehensive features for token sniping, wallet tracking, and automated trading.

## 🚀 Features

### Core Trading Features
- **Token Sniping**: Real-time new token detection and automated buying
- **Wallet Tracking**: Monitor specific wallets for copy trading opportunities  
- **Take-Profit & Stop-Loss**: Automated position management with customizable rules
- **Portfolio Management**: Track and manage multiple token positions
- **Risk Management**: Built-in safeguards and position sizing

### Advanced Features
- **Multi-Exchange Support**: Primary focus on AxiomTrade with extensible architecture
- **Real-time WebSocket**: Live price feeds and transaction monitoring
- **Discord Integration**: Notifications and bot control via Discord
- **Database Tracking**: Persistent storage for trades, profits, and analytics
- **Backtesting**: Test strategies against historical data
- **Configuration Management**: Flexible YAML-based configuration

## 📁 Project Structure

```
AxiomTradeBot/
├── axiomtradeapi/           # AxiomTrade API wrapper (existing)
├── bot/                     # Main bot modules
│   ├── core/               # Core bot functionality
│   ├── strategies/         # Trading strategies
│   ├── monitoring/         # Price and wallet monitoring
│   ├── risk_management/    # Risk and position management
│   └── notifications/      # Alert and notification systems
├── config/                 # Configuration files
├── data/                   # Database and data storage
├── tests/                  # Test suite
├── examples/              # Usage examples and tutorials
└── docs/                  # Documentation
```

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ChipaDevTeam/AxiomTradeBot.git
   cd AxiomTradeBot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the bot**
   ```bash
   cp config/config.example.yaml config/config.yaml
   # Edit config/config.yaml with your settings
   ```

## ⚙️ Configuration

Create a `config/config.yaml` file with your settings:

```yaml
# AxiomTrade API Configuration
axiom_trade:
  email: "your-email@example.com"
  password: "your-base64-encoded-password"
  
# Trading Configuration
trading:
  default_buy_amount: 0.1  # SOL
  max_position_size: 1.0   # SOL
  take_profit_percentage: 50.0
  stop_loss_percentage: 20.0
  
# Token Sniping
sniping:
  enabled: true
  min_liquidity: 5.0  # SOL
  max_buy_tax: 10.0   # %
  max_sell_tax: 10.0  # %
  
# Notifications
notifications:
  discord:
    enabled: true
    webhook_url: "your-discord-webhook-url"
```

## 🚀 Quick Start

### Basic Usage

```python
from bot.core.trading_bot import AxiomTradingBot
from bot.strategies.token_sniper import TokenSniper
from bot.strategies.wallet_tracker import WalletTracker

# Initialize the bot
bot = AxiomTradingBot(config_path="config/config.yaml")

# Add token sniping strategy
sniper = TokenSniper(bot)
bot.add_strategy(sniper)

# Add wallet tracking strategy
tracker = WalletTracker(bot, target_wallets=["wallet_address_1", "wallet_address_2"])
bot.add_strategy(tracker)

# Start the bot
await bot.start()
```

### Token Sniping Example

```python
from bot.strategies.token_sniper import TokenSniper

# Configure token sniper
sniper_config = {
    "buy_amount": 0.05,  # SOL
    "min_liquidity": 10.0,
    "max_buy_tax": 5.0,
    "take_profit": 100.0,  # %
    "stop_loss": 15.0      # %
}

sniper = TokenSniper(bot, config=sniper_config)
await sniper.start()
```

### Wallet Tracking Example

```python
from bot.strategies.wallet_tracker import WalletTracker

# Track profitable wallets
profitable_wallets = [
    "11111111111111111111111111111112",  # System program
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # Token program
]

tracker = WalletTracker(
    bot, 
    target_wallets=profitable_wallets,
    copy_percentage=50.0,  # Copy 50% of their trade size
    min_trade_size=0.01    # Minimum 0.01 SOL trades
)
await tracker.start()
```

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black bot/ tests/
flake8 bot/ tests/
```

### Adding New Strategies

1. Create a new strategy class inheriting from `BaseStrategy`
2. Implement required methods: `initialize()`, `execute()`, `cleanup()`
3. Add your strategy to the bot configuration

Example:
```python
from bot.core.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    async def initialize(self):
        # Setup strategy
        pass
        
    async def execute(self):
        # Main strategy logic
        pass
        
    async def cleanup(self):
        # Cleanup resources
        pass
```

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Contribution Guidelines

- Follow the existing code style and formatting
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting

## 📊 Features Roadmap

### Phase 1 (Current)
- [x] Token Sniping
- [x] Wallet Tracking  
- [x] Take-Profit & Stop-Loss
- [x] Basic Risk Management

### Phase 2 (Planned)
- [ ] Advanced Technical Analysis
- [ ] Machine Learning Models
- [ ] Multi-DEX Support
- [ ] Advanced Portfolio Optimization
- [ ] Web Dashboard Interface

### Phase 3 (Future)
- [ ] Mobile App
- [ ] Advanced Backtesting Engine
- [ ] Community Signal Sharing
- [ ] DeFi Yield Farming Integration

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk and may result in significant financial losses. Always do your own research and never invest more than you can afford to lose.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- AxiomTrade for providing the API
- The open-source community for inspiration and tools
- All contributors and testers

## 📞 Support

- **Discord**: [Join our community](https://discord.gg/your-invite)
- **Issues**: [GitHub Issues](https://github.com/your-username/AxiomTradeBot/issues)
- **Documentation**: [Full Documentation](https://docs.your-domain.com)

---

**Built with ❤️ by the community, for the community**
