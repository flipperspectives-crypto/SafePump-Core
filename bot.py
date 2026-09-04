import logging
import random
import sys
import time
from typing import Optional

import config
from dex_router import DEXRouter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("AxiomBNVBot")


class TradingBot:
    def __init__(self, router: Optional[DEXRouter] = None):
        errors = config.validate_config()
        if errors and not router:
            for err in errors:
                logger.error(f"Configuration error: {err}")
            raise ValueError("Invalid configuration. Please check .env file.")

        self.router = router or DEXRouter()
        self.entry_price: Optional[float] = None
        self.position_raw: int = 0

    def get_random_buy_amount(self) -> float:
        """Generates a random BNB trade size between MIN_BUY_AMOUNT_BNB and MAX_BUY_AMOUNT_BNB."""
        min_amount = config.MIN_BUY_AMOUNT_BNB
        max_amount = config.MAX_BUY_AMOUNT_BNB
        if min_amount >= max_amount:
            return min_amount
        return round(random.uniform(min_amount, max_amount), 4)

    def check_position(self) -> dict:
        """Inspects wallet's current target token balance and calculates position status."""
        raw_balance, formatted_balance, decimals = self.router.get_token_balance()
        current_price = self.router.get_token_price_in_bnb()

        pnl_percent = 0.0
        if self.entry_price and self.entry_price > 0 and raw_balance > 0:
            pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100.0

        return {
            "raw_balance": raw_balance,
            "formatted_balance": formatted_balance,
            "decimals": decimals,
            "current_price": current_price,
            "entry_price": self.entry_price,
            "pnl_percent": pnl_percent,
        }

    def evaluate_and_trade(self):
        """Core decision cycle for position management and automated trading."""
        status = self.check_position()
        raw_balance = status["raw_balance"]
        formatted_balance = status["formatted_balance"]
        current_price = status["current_price"]
        pnl_percent = status["pnl_percent"]

        logger.info(
            f"Token Balance: {formatted_balance:.4f} | "
            f"Current Price: {current_price:.8f} BNB | "
            f"Entry Price: {self.entry_price or 0.0:.8f} BNB | "
            f"PnL: {pnl_percent:+.2f}%"
        )

        if raw_balance > 0:
            # We hold a position; evaluate risk rules (Stop Loss / Take Profit)
            if self.entry_price is None:
                # Synchronize entry price if position was bought externally
                self.entry_price = current_price
                logger.info(f"Adopted current price {current_price:.8f} BNB as entry price.")
                return

            if pnl_percent <= -config.STOP_LOSS_PERCENT:
                logger.warning(
                    f"STOP-LOSS TRIGGERED! PnL ({pnl_percent:.2f}%) dropped below -{config.STOP_LOSS_PERCENT}%"
                )
                logger.info(f"Selling entire token balance: {formatted_balance:.4f}...")
                tx_hash = self.router.sell_token_for_bnb(raw_balance)
                logger.info(f"Stop-loss sell executed. Tx: {tx_hash}")
                self.entry_price = None
                self.position_raw = 0

            elif pnl_percent >= config.TAKE_PROFIT_PERCENT:
                logger.info(
                    f"TAKE-PROFIT TRIGGERED! PnL ({pnl_percent:.2f}%) reached +{config.TAKE_PROFIT_PERCENT}%"
                )
                logger.info(f"Selling entire token balance: {formatted_balance:.4f}...")
                tx_hash = self.router.sell_token_for_bnb(raw_balance)
                logger.info(f"Take-profit sell executed. Tx: {tx_hash}")
                self.entry_price = None
                self.position_raw = 0

            else:
                logger.info("Position active. Holding position according to risk strategy.")

        else:
            # No open position; evaluate executing a new buy order
            self.entry_price = None
            self.position_raw = 0

            bnb_balance = self.router.get_bnb_balance()
            buy_amount = self.get_random_buy_amount()

            if bnb_balance < buy_amount + 0.005:  # Reserve 0.005 BNB for gas
                logger.warning(
                    f"Insufficient BNB balance ({bnb_balance:.4f} BNB) for buy size {buy_amount:.4f} BNB + gas fee."
                )
                return

            logger.info(f"Initiating buy order for {buy_amount:.4f} BNB...")
            tx_hash = self.router.buy_token_with_bnb(buy_amount)
            logger.info(f"Buy executed successfully! Tx: {tx_hash}")

            # Record entry price
            self.entry_price = current_price
            logger.info(f"Updated entry price to {self.entry_price:.8f} BNB")

    def run(self):
        """Main automation execution loop."""
        logger.info("Starting Axiom BNB V2 Trading Bot...")
        logger.info(f"Target Token: {config.TARGET_TOKEN_ADDRESS}")
        logger.info(f"Router Address: {config.ROUTER_ADDRESS}")
        logger.info(
            f"Risk Limits -> Stop Loss: -{config.STOP_LOSS_PERCENT}%, Take Profit: +{config.TAKE_PROFIT_PERCENT}%"
        )

        while True:
            try:
                self.evaluate_and_trade()
            except Exception as e:
                logger.error(f"Error during bot loop execution: {e}", exc_info=True)

            logger.info(f"Sleeping for {config.CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(config.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        bot = TradingBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot manually stopped by user. Exiting cleanly.")
        sys.exit(0)
