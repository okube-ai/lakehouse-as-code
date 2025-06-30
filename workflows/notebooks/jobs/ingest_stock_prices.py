# COMMAND ----------
dbutils.widgets.text("env", "dev")

# COMMAND ----------
# MAGIC %pip install yfinance /Workspace/.laktory/wheels/lake-0.0.1-py3-none-any.whl
# MAGIC %restart_python

# COMMAND ----------
import os
import yfinance as yf
from datetime import datetime
from datetime import date
from datetime import timedelta

from lake import DataEvent
from lake import DataProducer


# --------------------------------------------------------------------------- #
# Setup                                                                       #
# --------------------------------------------------------------------------- #

env = dbutils.widgets.get("env")

symbols = [
    "AAPL",
    "AMZN",
    "GOOGL",
    "MSFT",
]

today = date.today()
t1 = datetime(today.year, today.month, today.day)
t0 = t1 - timedelta(days=3)

for s in symbols:
    # ----------------------------------------------------------------------- #
    # Fetch events                                                            #
    # ----------------------------------------------------------------------- #

    events = []
    df = yf.download(s, t0, t1, interval="1h")
    for _, row in df.iterrows():

        # Corrupt some data to showcase expectations
        if _.date() == date(2024, 4, 1):
            row["Open"] *= -1
            row["Close"] *= -1
            row["High"] *= -1
            row["Low"] *= -1

        events += [
            DataEvent(
                name="stock_price",
                producer=DataProducer(name="yahoo-finance"),
                events_root=f"/Volumes/{env}/sources/landing/events/",
                data={
                    "created_at": _,
                    "symbol": s,
                    "open": float(
                        row["Open"]
                    ),  # np.float64 are not supported for serialization
                    "close": float(row["Close"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "volume": float(row["Volume"]),
                },
            )
        ]

    # --------------------------------------------------------------------------- #
    # Write events                                                                #
    # --------------------------------------------------------------------------- #

    for event in events:
        event.to_databricks(suffix=s, skip_if_exists=True)
