# COMMAND ----------
# MAGIC %pip yfinance

# COMMAND ----------
import yfinance as yf

from laktory.models import DataEvent
from laktory.models import DataProducer


# --------------------------------------------------------------------------- #
# Setup                                                                       #
# --------------------------------------------------------------------------- #

symbols = [
    "AAPL",
    "AMZN",
    "GOOGL",
    "MSFT",
]

for s in symbols:
    print(s)
    ticker = yf.Ticker(s)

    data = ticker.history_metadata
    del data["tradingPeriods"]

    event = DataEvent(
        name="stock_metadata",
        producer=DataProducer(name="yahoo-finance"),
        data=data,
        tstamp_in_path=False,
    )
    event.to_databricks(overwrite=True, suffix=s)
