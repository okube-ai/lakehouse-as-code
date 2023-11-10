import os
import yfinance as yf
from datetime import datetime
from datetime import date
from datetime import timedelta

from laktory.models import DataEvent
from laktory.models import Producer


# --------------------------------------------------------------------------- #
# Setup                                                                       #
# --------------------------------------------------------------------------- #

symbols = [
    "AAPL",
    "AMZN",
    "GOOGL",
    "MSFT",
]


class DatelessDataEvent(DataEvent):

    @property
    def dirpath(self) -> str:
        return f"{self.event_root}"

    def get_filename(self, fmt="json", suffix=None) -> str:
        prefix = self.name
        if suffix is not None:
            prefix += f"_{suffix}"
        if fmt == "json_stream":
            fmt = "txt"
        return f"{prefix}.{fmt}"


for s in symbols:
    print(s)
    ticker = yf.Ticker(s)

    data = ticker.history_metadata
    del data["tradingPeriods"]

    event = DatelessDataEvent(
        name="stock_metadata",
        producer=Producer(name="yahoo-finance"),
        data=data,
    )
    event.to_databricks(overwrite=True, suffix=s)

