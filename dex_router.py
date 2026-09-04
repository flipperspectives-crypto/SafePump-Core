import json
import logging
import time
from typing import Tuple, Optional
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account

import config

logger = logging.getLogger("DEXRouter")


class DEXRouter:
    def __init__(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None):
        self.rpc_url = rpc_url or config.BSC_RPC_URL
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC node at {self.rpc_url}")

        chain_id = self.w3.eth.chain_id
        logger.info(f"Connected to network with Chain ID: {chain_id}")
        if chain_id != config.CHAIN_ID:
            logger.warning(
                f"Chain ID mismatch! Expected {config.CHAIN_ID}, got {chain_id}. Proceeding with caution."
            )

        self.private_key = private_key or config.PRIVATE_KEY
        if self.private_key:
            self.account = Account.from_key(self.private_key)
            self.wallet_address = self.account.address
            logger.info(f"Wallet loaded: {self.wallet_address}")
        else:
            self.account = None
            self.wallet_address = None
            logger.warning("No private key provided; read-only mode activated.")

        # Load ABIs
        with open("router_abi.json", "r") as f:
            self.router_abi = json.load(f)
        with open("erc20_abi.json", "r") as f:
            self.erc20_abi = json.load(f)

        self.router_address = Web3.to_checksum_address(config.ROUTER_ADDRESS)
        self.wbnb_address = Web3.to_checksum_address(config.WBNB_ADDRESS)
        self.target_token_address = (
            Web3.to_checksum_address(config.TARGET_TOKEN_ADDRESS)
            if config.TARGET_TOKEN_ADDRESS
            else None
        )

        self.router_contract = self.w3.eth.contract(
            address=self.router_address, abi=self.router_abi
        )

    def get_token_contract(self, token_address: str):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=self.erc20_abi
        )

    def get_bnb_balance(self, address: Optional[str] = None) -> float:
        addr = address or self.wallet_address
        if not addr:
            raise ValueError("No wallet address provided.")
        balance_wei = self.w3.eth.get_balance(addr)
        return float(Web3.from_wei(balance_wei, "ether"))

    def get_token_balance(
        self, token_address: Optional[str] = None, address: Optional[str] = None
    ) -> Tuple[int, float, int]:
        """Returns raw balance, formatted balance, and token decimals."""
        addr = address or self.wallet_address
        token_addr = token_address or self.target_token_address
        if not addr or not token_addr:
            raise ValueError("Wallet and token address must be specified.")

        token_contract = self.get_token_contract(token_addr)
        decimals = token_contract.functions.decimals().call()
        raw_balance = token_contract.functions.balanceOf(addr).call()
        formatted_balance = raw_balance / (10**decimals)
        return raw_balance, formatted_balance, decimals

    def get_estimated_amounts_out(
        self, amount_in_wei: int, path: list
    ) -> list:
        """Fetches expected output amounts for a given input amount along a trade path."""
        checksum_path = [Web3.to_checksum_address(addr) for addr in path]
        return self.router_contract.functions.getAmountsOut(
            amount_in_wei, checksum_path
        ).call()

    def get_token_price_in_bnb(
        self, token_address: Optional[str] = None
    ) -> float:
        """Calculates the price of 1 full unit of token in BNB."""
        token_addr = token_address or self.target_token_address
        if not token_addr:
            raise ValueError("Target token address not configured.")

        token_contract = self.get_token_contract(token_addr)
        decimals = token_contract.functions.decimals().call()
        one_token_wei = 10**decimals

        path = [token_addr, self.wbnb_address]
        amounts = self.get_estimated_amounts_out(one_token_wei, path)
        bnb_out_wei = amounts[-1]
        return float(Web3.from_wei(bnb_out_wei, "ether"))

    def calculate_min_amount_out(
        self, amount_out_wei: int, slippage_percent: Optional[float] = None
    ) -> int:
        slippage = (
            slippage_percent if slippage_percent is not None else config.SLIPPAGE_PERCENT
        )
        multiplier = (100.0 - slippage) / 100.0
        return int(amount_out_wei * multiplier)

    def approve_token_if_needed(
        self, token_address: str, amount_wei: int
    ) -> Optional[str]:
        """Approves router contract to spend tokens if current allowance is insufficient."""
        if not self.account:
            raise ValueError("Private key required for approval.")

        token_contract = self.get_token_contract(token_address)
        allowance = token_contract.functions.allowance(
            self.wallet_address, self.router_address
        ).call()

        if allowance >= amount_wei:
            logger.info("Sufficient allowance already approved.")
            return None

        logger.info(
            f"Approving router {self.router_address} to spend {amount_wei} tokens..."
        )
        nonce = self.w3.eth.get_transaction_count(self.wallet_address)
        gas_price = (
            self.w3.to_wei(config.GAS_PRICE_GWEI, "gwei")
            if config.GAS_PRICE_GWEI > 0
            else self.w3.eth.gas_price
        )

        approve_txn = token_contract.functions.approve(
            self.router_address, amount_wei
        ).build_transaction(
            {
                "from": self.wallet_address,
                "nonce": nonce,
                "gas": config.GAS_LIMIT,
                "gasPrice": gas_price,
                "chainId": config.CHAIN_ID,
            }
        )

        signed_txn = self.w3.eth.account.sign_transaction(
            approve_txn, private_key=self.private_key
        )
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        logger.info(f"Approval transaction sent. Tx Hash: {tx_hash.hex()}")

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        logger.info(f"Approval confirmed in block {receipt.blockNumber}")
        return tx_hash.hex()

    def buy_token_with_bnb(
        self,
        bnb_amount: float,
        target_token: Optional[str] = None,
        slippage_percent: Optional[float] = None,
    ) -> str:
        """Executes a buy order swapping BNB for target token via router."""
        if not self.account:
            raise ValueError("Private key required for executing trades.")

        token_addr = target_token or self.target_token_address
        if not token_addr:
            raise ValueError("Target token address not specified.")

        token_checksum = Web3.to_checksum_address(token_addr)
        amount_in_wei = self.w3.to_wei(bnb_amount, "ether")
        path = [self.wbnb_address, token_checksum]

        amounts_out = self.get_estimated_amounts_out(amount_in_wei, path)
        expected_out_wei = amounts_out[-1]
        min_out_wei = self.calculate_min_amount_out(expected_out_wei, slippage_percent)

        deadline = int(time.time()) + 600  # 10 minutes deadline
        nonce = self.w3.eth.get_transaction_count(self.wallet_address)
        gas_price = (
            self.w3.to_wei(config.GAS_PRICE_GWEI, "gwei")
            if config.GAS_PRICE_GWEI > 0
            else self.w3.eth.gas_price
        )

        swap_func = self.router_contract.functions.swapExactETHForTokens(
            min_out_wei, path, self.wallet_address, deadline
        )

        try:
            estimated_gas = swap_func.estimate_gas(
                {"from": self.wallet_address, "value": amount_in_wei}
            )
            gas_limit = int(estimated_gas * 1.2)
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}. Using configured GAS_LIMIT.")
            gas_limit = config.GAS_LIMIT

        txn = swap_func.build_transaction(
            {
                "from": self.wallet_address,
                "value": amount_in_wei,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": config.CHAIN_ID,
            }
        )

        signed_txn = self.w3.eth.account.sign_transaction(
            txn, private_key=self.private_key
        )
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        logger.info(f"Buy transaction sent. Tx Hash: {tx_hash.hex()}")
        return tx_hash.hex()

    def sell_token_for_bnb(
        self,
        token_amount_raw: int,
        target_token: Optional[str] = None,
        slippage_percent: Optional[float] = None,
    ) -> str:
        """Executes a sell order swapping target token for BNB via router."""
        if not self.account:
            raise ValueError("Private key required for executing trades.")

        token_addr = target_token or self.target_token_address
        if not token_addr:
            raise ValueError("Target token address not specified.")

        token_checksum = Web3.to_checksum_address(token_addr)
        self.approve_token_if_needed(token_checksum, token_amount_raw)

        path = [token_checksum, self.wbnb_address]
        amounts_out = self.get_estimated_amounts_out(token_amount_raw, path)
        expected_out_wei = amounts_out[-1]
        min_out_wei = self.calculate_min_amount_out(expected_out_wei, slippage_percent)

        deadline = int(time.time()) + 600
        nonce = self.w3.eth.get_transaction_count(self.wallet_address)
        gas_price = (
            self.w3.to_wei(config.GAS_PRICE_GWEI, "gwei")
            if config.GAS_PRICE_GWEI > 0
            else self.w3.eth.gas_price
        )

        swap_func = self.router_contract.functions.swapExactTokensForETH(
            token_amount_raw, min_out_wei, path, self.wallet_address, deadline
        )

        try:
            estimated_gas = swap_func.estimate_gas({"from": self.wallet_address})
            gas_limit = int(estimated_gas * 1.2)
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}. Using configured GAS_LIMIT.")
            gas_limit = config.GAS_LIMIT

        txn = swap_func.build_transaction(
            {
                "from": self.wallet_address,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": config.CHAIN_ID,
            }
        )

        signed_txn = self.w3.eth.account.sign_transaction(
            txn, private_key=self.private_key
        )
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        logger.info(f"Sell transaction sent. Tx Hash: {tx_hash.hex()}")
        return tx_hash.hex()
