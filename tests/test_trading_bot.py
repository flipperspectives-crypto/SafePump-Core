import os
import unittest
from unittest.mock import MagicMock, patch

import config
from dex_router import DEXRouter
from bot import TradingBot


class TestTradingBot(unittest.TestCase):

    def test_config_loading(self):
        """Verify environment config parsing and default fallback values."""
        self.assertEqual(config.CHAIN_ID, 56)
        self.assertIn("bsc", config.BSC_RPC_URL.lower())
        errors = config.validate_config()
        self.assertIsInstance(errors, list)

    def test_slippage_calculation(self):
        """Verify minimum amount out calculation based on slippage tolerance percentage."""
        with patch.object(DEXRouter, "__init__", lambda self, *args, **kwargs: None):
            router = DEXRouter()

            # 100 units expected output, 1% slippage -> 99 min out
            min_out = router.calculate_min_amount_out(1000000, slippage_percent=1.0)
            self.assertEqual(min_out, 990000)

            # 5% slippage -> 95 min out
            min_out_5 = router.calculate_min_amount_out(1000000, slippage_percent=5.0)
            self.assertEqual(min_out_5, 950000)

    def test_random_trade_sizing(self):
        """Verify random trade sizing generates amounts within min/max bounds."""
        with patch.object(DEXRouter, "__init__", lambda self, *args, **kwargs: None):
            mock_router = DEXRouter()
            with patch("config.MIN_BUY_AMOUNT_BNB", 0.01), patch("config.MAX_BUY_AMOUNT_BNB", 0.05):
                with patch("config.validate_config", return_value=[]):
                    bot = TradingBot(router=mock_router)
                    for _ in range(50):
                        size = bot.get_random_buy_amount()
                        self.assertGreaterEqual(size, 0.01)
                        self.assertLessEqual(size, 0.05)

    def test_stop_loss_trigger(self):
        """Verify sell signal is triggered when PnL drops below stop loss threshold."""
        mock_router = MagicMock(spec=DEXRouter)
        mock_router.get_token_balance.return_value = (1000000000000000000, 1.0, 18)
        # Entry price 1.0 BNB, current price 0.85 BNB -> -15% PnL (Stop loss is 10%)
        mock_router.get_token_price_in_bnb.return_value = 0.85
        mock_router.sell_token_for_bnb.return_value = "0xmocktxhashstoploss"

        with patch("config.validate_config", return_value=[]):
            bot = TradingBot(router=mock_router)
            bot.entry_price = 1.0
            bot.evaluate_and_trade()

            mock_router.sell_token_for_bnb.assert_called_once_with(1000000000000000000)
            self.assertIsNone(bot.entry_price)

    def test_take_profit_trigger(self):
        """Verify sell signal is triggered when PnL exceeds take profit threshold."""
        mock_router = MagicMock(spec=DEXRouter)
        mock_router.get_token_balance.return_value = (1000000000000000000, 1.0, 18)
        # Entry price 1.0 BNB, current price 1.25 BNB -> +25% PnL (Take profit is 20%)
        mock_router.get_token_price_in_bnb.return_value = 1.25
        mock_router.sell_token_for_bnb.return_value = "0xmocktxhashtakeprofit"

        with patch("config.validate_config", return_value=[]):
            bot = TradingBot(router=mock_router)
            bot.entry_price = 1.0
            bot.evaluate_and_trade()

            mock_router.sell_token_for_bnb.assert_called_once_with(1000000000000000000)
            self.assertIsNone(bot.entry_price)

    def test_router_swap_encoding(self):
        """Verify router buy order method builds and signs transaction correctly."""
        with patch("web3.Web3.HTTPProvider"), patch("web3.Web3.is_connected", return_value=True):
            mock_w3 = MagicMock()
            mock_w3.eth.chain_id = 56
            mock_w3.to_wei.side_effect = lambda val, unit: int(val * 10**18)
            mock_w3.eth.get_transaction_count.return_value = 1
            mock_w3.eth.gas_price = 3000000000
            mock_w3.eth.send_raw_transaction.return_value = b"\x12\x34\x56\x78"

            mock_account = MagicMock()
            mock_account.address = "0x1111111111111111111111111111111111111111"

            with patch("dex_router.Web3", return_value=mock_w3) as mock_web3_class:
                mock_web3_class.to_checksum_address = lambda addr: addr
                mock_web3_class.from_wei = lambda val, unit: val / 10**18

                with patch.object(DEXRouter, "__init__", lambda self, *args, **kwargs: None):
                    router = DEXRouter()
                    router.w3 = mock_w3
                    router.account = mock_account
                    router.wallet_address = mock_account.address
                    router.private_key = "0x" + "1" * 64
                    router.wbnb_address = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
                    router.target_token_address = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
                    router.get_estimated_amounts_out = MagicMock(return_value=[10000000000000000, 500000000000000000000])
                    router.calculate_min_amount_out = MagicMock(return_value=495000000000000000000)

                    mock_contract = MagicMock()
                    mock_swap_func = MagicMock()
                    mock_swap_func.estimate_gas.return_value = 150000
                    mock_swap_func.build_transaction.return_value = {"to": "0xRouter", "data": "0x1234"}
                    mock_contract.functions.swapExactETHForTokens.return_value = mock_swap_func
                    router.router_contract = mock_contract

                    tx_hash = router.buy_token_with_bnb(0.01)
                    self.assertEqual(tx_hash, "12345678")


if __name__ == "__main__":
    unittest.main()
