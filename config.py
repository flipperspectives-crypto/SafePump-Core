import os
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

# BSC Network Settings
BSC_RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
CHAIN_ID = int(os.getenv("CHAIN_ID", "56"))

# Wallet Settings
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")

# Router and Token Addresses
# Axiom BNB V2 Router or standard BSC V2 Router address
ROUTER_ADDRESS = os.getenv("ROUTER_ADDRESS", "0x10ED433D51B191656629E9baeC6544610146585c")
# Wrapped BNB on BSC Mainnet
WBNB_ADDRESS = os.getenv("WBNB_ADDRESS", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
# Target Token address to trade against WBNB / BNB
TARGET_TOKEN_ADDRESS = os.getenv("TARGET_TOKEN_ADDRESS", "")

# Trading Parameters
SLIPPAGE_PERCENT = float(os.getenv("SLIPPAGE_PERCENT", "1.0"))  # Default 1% slippage
GAS_PRICE_GWEI = float(os.getenv("GAS_PRICE_GWEI", "3.0"))      # Gas price in Gwei (0 for dynamic estimation)
GAS_LIMIT = int(os.getenv("GAS_LIMIT", "300000"))               # Max gas limit for trades

# Automation & Risk Management
MIN_BUY_AMOUNT_BNB = float(os.getenv("MIN_BUY_AMOUNT_BNB", "0.01"))
MAX_BUY_AMOUNT_BNB = float(os.getenv("MAX_BUY_AMOUNT_BNB", "0.05"))
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "10"))

STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "10.0"))   # Trigger sell if loss exceeds 10%
TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", "20.0")) # Trigger sell if profit exceeds 20%


def validate_config():
    """Validates basic requirements in configuration."""
    errors = []
    if not PRIVATE_KEY:
        errors.append("PRIVATE_KEY environment variable is not set.")
    if not TARGET_TOKEN_ADDRESS:
        errors.append("TARGET_TOKEN_ADDRESS environment variable is not set.")
    return errors
