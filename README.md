[![Sponsor](https://img.shields.io/badge/Sponsor-❤%20flipperspectives-2ecc71)](https://github.com/sponsors/flipperspectives-crypto)

# SafePump-Core & Axiom BNB V2 Trading Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![good first issues](https://img.shields.io/github/issues/Nosferatus1988/SafePump-Core/good-first-issue?label=good%20first%20issues)](https://github.com/Nosferatus1988/SafePump-Core/issues?q=is%3Aissue+is%3Aopen+label%3A%22good-first-issue%22)

SafePump-Core is an anti-MEV bonding-curve launchpad on Solana, paired with a modular Python-based trading bot for BNB Smart Chain (BSC) targeting the new **Axiom BNB V2** exchange release.

---

## 🤖 Axiom BNB V2 Trading Bot (BSC)

The Python trading bot automates token trading on BSC (Chain ID 56) with custom RPC support, secure `.env` key loading, random trade sizing, slippage tolerance protection, and automated stop-loss / take-profit risk rules.

### Features
- **Web3.py Integration**: Native integration with BNB Smart Chain (Chain ID 56) and support for custom RPC endpoints.
- **Secure Wallet Management**: Private key management loaded securely via `.env`.
- **Modular Router Interface (`dex_router.py`)**: Interacts with Axiom / PancakeSwap V2 style router contracts (`swapExactETHForTokens`, `swapExactTokensForETH`, `getAmountsOut`, and ERC-20 approvals).
- **Automated Trading Loop (`bot.py`)**:
  - Configurable check intervals.
  - Randomized order sizing between configurable min/max BNB bounds.
  - Position monitoring with automatic **Stop-Loss** and **Take-Profit** execution.
- **Unit Testing**: Suite of automated unit tests using `pytest` / `unittest`.

### Directory Structure
- `config.py`: Environment variable parser and default configuration settings.
- `dex_router.py`: DEX router client for Web3 queries, token pricing, approvals, and order execution.
- `bot.py`: Automation loop for position tracking, trade evaluation, and risk enforcement.
- `router_abi.json`: ABI definition for Uniswap/PancakeSwap V2 / Axiom router functions.
- `erc20_abi.json`: ABI definition for ERC-20 token standard functions.
- `.env.example`: Configuration template.
- `tests/test_trading_bot.py`: Comprehensive test suite.

### Quick Start Guide

1. **Install Python Dependencies**:
   ```bash
   pip install web3 python-dotenv
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your wallet private key, target token address, and desired risk settings:
   ```bash
   cp .env.example .env
   ```

   Configuration Options in `.env`:
   - `BSC_RPC_URL`: BSC RPC provider URL (default: `https://bsc-dataseed.binance.org/`).
   - `CHAIN_ID`: Chain ID (`56` for BSC Mainnet).
   - `PRIVATE_KEY`: Private key of your BSC trading wallet.
   - `ROUTER_ADDRESS`: Axiom BNB V2 / DEX Router Contract Address.
   - `TARGET_TOKEN_ADDRESS`: Contract address of the token you want to trade.
   - `SLIPPAGE_PERCENT`: Maximum allowed slippage tolerance percentage (e.g. `1.0` for 1%).
   - `MIN_BUY_AMOUNT_BNB` & `MAX_BUY_AMOUNT_BNB`: Random buy transaction range in BNB.
   - `STOP_LOSS_PERCENT`: Trigger sell when PnL drops below this % (e.g. `10.0` for -10%).
   - `TAKE_PROFIT_PERCENT`: Trigger sell when PnL reaches or exceeds this % (e.g. `20.0` for +20%).
   - `CHECK_INTERVAL_SECONDS`: Delay between monitoring cycles in seconds.

3. **Run Unit Tests**:
   ```bash
   python3 -m unittest discover -s tests -p "test_*.py"
   ```

4. **Launch Trading Bot**:
   ```bash
   python3 bot.py
   ```

---

## 🛠️ SafePump-Core Solana Launchpad

Anti-MEV bonding-curve launchpad on Solana, written in Anchor/Rust.

This repository is a devnet MVP. It can initialize a launch, route first-slot
snipes into a vesting vault, let normal buyers buy and sell on the bonding
curve, and mark a curve complete when an optional graduation target is reached.

🌐 Live site: [safepump-core.com](https://www.safepump-core.com)

### Program ID

`FMAhGG8ETyqnd4zan4HBdLRPEQvk7Cvc6kzWbsvnXj5q`

Deployed on devnet with upgrade authority
`9WPztx4YNSrLr1ZD61kKziwqryQhrrTPomx6HodyJCS9`.

### Anti-MEV model

Token launches on Solana get sniped in the first slots by bots that buy a large
piece of supply, wait for organic buyers to move price, and dump. SafePump
punishes that pattern by routing buys inside a tight post-launch window into a
time-locked vesting vault.

- Snipe window: first `SNIPE_WINDOW_SLOTS = 10` slots after `initialize_curve`.
- Penalty: sniped tokens go to a `VestingVault` PDA instead of the buyer wallet.
- Lock duration: `VESTING_DURATION_SECONDS = 48 * 3600`.
- Repeat sniping: every snipe by the same wallet resets the unlock timestamp.

### Bonding curve

Virtual constant-product curve:

```text
tokens_out = vtok - ceil((vsol * vtok) / (vsol + sol_in))
sol_out    = vsol - ceil((vsol * vtok) / (vtok + tokens_in))
```

### Devnet setup

Install JS dependencies:

```bash
npm install
```

Build and test locally:

```bash
npm run build
npm test
```
