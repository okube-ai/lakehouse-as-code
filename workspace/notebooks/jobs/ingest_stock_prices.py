import os
import yfinance as yf
from datetime import datetime
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

t1 = datetime(2023, 10, 20)
t0 = t1 - timedelta(days=3)

# --------------------------------------------------------------------------- #
# Fetch events                                                                #
# --------------------------------------------------------------------------- #

events = []
for s in symbols:
    df = yf.download(s, t0, t1, interval="1m")
    for _, row in df.iterrows():
        events += [
            DataEvent(
                name="stock_price",
                producer=Producer(name="yahoo-finance"),
                data={
                    "created_at": _,
                    "symbol": s,
                    "open": float(
                        row["Open"]
                    ),  # np.float64 are not supported for serialization
                    "close": float(row["Close"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                },
            )
        ]


# --------------------------------------------------------------------------- #
# Write events                                                                #
# --------------------------------------------------------------------------- #

for event in events:
    event.to_databricks(skip_if_exists=True)
