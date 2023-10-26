from decimal import Decimal
import pandas as pd
import numpy as np

from datetime import datetime, timedelta

from quantfreedom.enums import ExchangeSettings

UNIVERSAL_SIDES = ["buy", "sell"]
UNIVERSAL_TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "d", "w", "m"]
TIMEFRAMES_IN_MINUTES = [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440, 10080, 43800]


class Exchange:
    candles_list = None
    volume_yes_no_start = None
    volume_yes_no_end = None
    exchange_settings: ExchangeSettings = None

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        use_test_net: bool,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.use_test_net = use_test_net

    def get_candles(self, **vargs):
        pass

    def cancel_open_order(self, *vargs):
        pass

    def get_filled_orders_by_order_id(self, *vargs):
        pass

    def move_open_order(self, *vargs):
        pass

    def get_open_order_by_order_id(self, *vargs):
        pass

    def cancel_all_open_order_per_symbol(self, *vargs):
        pass

    def get_wallet_info_of_asset(self, *vargs):
        pass

    def check_if_order_filled(self, *vargs):
        pass

    def set_leverage_value(self, *vargs):
        pass

    def check_if_order_canceled(self, *vargs):
        pass

    def check_if_order_open(self, *vargs):
        pass

    def get_equity_of_asset(self, *vargs):
        pass

    def move_stop_order(self, *vargs):
        pass

    def get_latest_pnl_result(self, *vargs):
        pass

    def get_closed_pnl(self, *vargs):
        pass

    def get_current_time_seconds(self):
        return int(datetime.now().timestamp())

    def get_current_time_ms(self):
        return self.get_current_time_seconds() * 1000

    def get_current_pd_datetime(self):
        return pd.to_datetime(self.get_current_time_seconds(), unit="s")

    def get_ms_time_to_pd_datetime(self, time_in_ms):
        return pd.to_datetime(time_in_ms / 1000, unit="s")

    def turn_candles_list_to_pd(self, candles_np):
        candles_df = pd.DataFrame(candles_np)
        candles_df["datetime"] = self.get_ms_time_to_pd_datetime(candles_df["timestamp"])
        candles_df.set_index("datetime", inplace=True)
        return candles_df

    def get_candles_to_dl_in_ms(self, candles_to_dl: int, timeframe_in_ms, limit: int):
        if candles_to_dl is not None:
            return candles_to_dl * timeframe_in_ms
        else:
            return timeframe_in_ms * limit

    def get_timeframe_in_ms(self, timeframe):
        timeframe_in_ms = int(
            timedelta(minutes=TIMEFRAMES_IN_MINUTES[UNIVERSAL_TIMEFRAMES.index(timeframe)]).seconds * 1000
        )
        return timeframe_in_ms

    def get_exchange_timeframe(self, ex_timeframe, timeframe):
        try:
            timeframe = ex_timeframe[UNIVERSAL_TIMEFRAMES.index(timeframe)]
        except Exception as e:
            Exception(f"Use one of these timeframes - {UNIVERSAL_TIMEFRAMES} -> {e}")
        return timeframe
