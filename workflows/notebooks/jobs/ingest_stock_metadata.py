# COMMAND ----------
dbutils.widgets.text("env", "dev")

# COMMAND ----------
# MAGIC %pip install yfinance /Workspace/.laktory/wheels/lake-0.0.1-py3-none-any.whl
# MAGIC %restart_python

# COMMAND ----------
import yfinance as yf

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
        events_root=f"/Volumes/{env}/sources/landing/events/",
    )
    event.to_databricks(overwrite=True, suffix=s)
