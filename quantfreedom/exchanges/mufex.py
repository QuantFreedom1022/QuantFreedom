import time
import hashlib
import hmac
import uuid

import pandas as pd
import numpy as np

from datetime import datetime, timedelta
from requests import get

mufex_timeframes = [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440, 10080, 43800]
universal_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "d", "w", "m"]


class Mufex:
    end_point = ""

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        category: str = "linear",
        timeframe: str = "5m",
        apikey: str = "",
        secret_key: str = "",
        use_test_net: bool = False,
        keep_volume_in_candles: bool = False,
    ):
        self.api_key = apikey
        self.secret_key = secret_key
        self.symbol = symbol
        self.category = category
        self.volume_yes_no = -2
        main_net = "https://api.mufex.finance/"  # Testnet endpoint
        test_net = "https://api.testnet.mufex.finance"  # Testnet endpoint
        self.url_start = main_net

        if use_test_net:
            self.url_start = test_net
        if keep_volume_in_candles:
            self.volume_yes_no = -1
        try:
            self.timeframe = mufex_timeframes[universal_timeframes.index(timeframe)]
            self.timeframe_in_ms = timedelta(minutes=self.timeframe).seconds * 1000
        except:
            raise TypeError(f"You need to send the following {universal_timeframes}")

    def get_candles(
        self,
        candles_to_dl: int = None,
        since_date_ms: int = None,
        until_date_ms: int = None,
    ):
        end_point = "public/v1/market/kline"
        candles_list = []
        if until_date_ms is None:
            until_date_ms = int(datetime.now().timestamp() * 1000) - self.timeframe_in_ms

        if since_date_ms is None and candles_to_dl is not None:
            since_date_ms = until_date_ms - self.timeframe_in_ms * candles_to_dl
        else:
            since_date_ms = until_date_ms - self.timeframe_in_ms * 200

        since_pd_timestamp = pd.to_datetime(int(since_date_ms / 1000), unit="s")
        until_pd_timestamp = pd.to_datetime(int(until_date_ms / 1000), unit="s")

        params = {
            "category": self.category,
            "symbol": self.symbol,
            "interval": self.timeframe,
            # 'limit': 200,
            "end": until_date_ms,
        }
        print(f"since_date_ms={since_pd_timestamp}, until_date_ms={until_pd_timestamp}")
        start_time = int(datetime.now().timestamp())
        while since_date_ms < until_date_ms:
            params["start"] = since_date_ms
            try:
                new_candles = get(url=self.url_start + end_point + "?", params=params).json()["data"]["list"]
            except Exception as e:
                print(f"Got exception -> {repr(e)}")
                break

            if new_candles is None:
                print(f"Got 0 candles")
                break
            else:
                print(f"Got {len(new_candles)} new candles for since={since_pd_timestamp}")
                candles_list.extend(new_candles)
                since_date_ms = int(candles_list[-1][0]) + 1000
                since_pd_timestamp = pd.to_datetime(since_date_ms, unit="ms")
                print(f"Getting candles since={since_pd_timestamp}")

        # if until_date_ms - int(candles_list[-1][0]) < 0:
        #     print("revmoing last candle because it is the current candle")
        #     candles_list = candles_list[:-1]
        # else:
        #     print("last candle is the right candle")
        candles_df = self.__candles_list_to_pd(candles_list=candles_list)
        print(
            f"It took {round((int(datetime.now().timestamp()) - start_time)/60,2)} minutes to create the candles dataframe"
        )
        return candles_df

    def __candles_list_to_pd(self, candles_list):
        candles = np.array(candles_list, dtype=np.float_)[:, : self.volume_yes_no]
        candles_df = pd.DataFrame(np.array(candles), columns=["timestamp", "open", "high", "low", "close"])
        candles_df = candles_df.astype({"timestamp": "int64"})
        candles_df.timestamp = pd.to_datetime(candles_df.timestamp, unit="ms")
        return candles_df

    def __get_HTTP_request(self, params, info):
        time_stamp = str(int(time.time() * 10**3))
        param_str = str(time_stamp) + "5000"
        hash = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
        signature = hash.hexdigest()
        headers = {
            "MF-ACCESS-API-KEY": self.api_key,
            "MF-ACCESS-SIGN": signature,
            "MF-ACCESS-SIGN-TYPE": "2",
            "MF-ACCESS-TIMESTAMP": time_stamp,
            "MF-ACCESS-RECV-WINDOW": "5000",
            "Content-Type": "application/json",
        }

        response = get(
            url=self.url_start + self.end_point + "?",
            params=params,
            headers=headers,
        )
        print(info + " Elapsed Time : " + str(response.elapsed))
        return response.json()