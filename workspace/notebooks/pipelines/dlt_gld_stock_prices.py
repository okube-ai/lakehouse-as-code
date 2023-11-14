import os
import pyspark.sql.functions as F

from laktory import dlt
from laktory import get_logger

dlt.spark = spark
logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Setup                                                                       #
# --------------------------------------------------------------------------- #

# Required to filter windows
spark.conf.set("spark.sql.session.timeZone", "UTC")

ws_env = os.getenv("LAKTORY_WORKSPACE_ENV")

METRICS = {
    "count": {
        "func": F.count,
        "args": (F.col("symbol"),),
        "fill": 0,
    },
    "low": {
        "func": F.min,
        "args": (F.col("low"),),
        "fill": 0,
    },
    "high": {
        "func": F.max,
        "args": (F.col("high"),),
        "fill": 0,
    },
    "open": {
        "func": F.first,
        "args": (F.col("open"),),
        "fill": 0,
    },
    "close": {
        "func": F.last,
        "args": (F.col("close"),),
        "fill": 0,
    },
}

# --------------------------------------------------------------------------- #
# Account Balances                                                            #
# --------------------------------------------------------------------------- #


def define_table(td, key):
    # Table name
    table_name = f"gld_stock_prices_by"
    if key is not None:
        table_name += f"_{key}"

    @dlt.table(
        name=table_name,
        table_properties={},
    )
    def get_df(td=td):

        logger.info(f"Building {table_name}")

        # ------------------------------------------------------------------- #
        # Read data                                                           #
        # ------------------------------------------------------------------- #

        logger.info("Reading data")

        df = dlt.read_stream(f"{ws_env}.finance.slv_star_stock_prices")

        # ------------------------------------------------------------------- #
        # Process data                                                        #
        # ------------------------------------------------------------------- #

        df = aggregate(df, td)

        # ------------------------------------------------------------------- #
        # Output                                                              #
        # ------------------------------------------------------------------- #

        return df

    return get_df


# --------------------------------------------------------------------------- #
# Aggregate                                                                   #
# --------------------------------------------------------------------------- #

def aggregate(df, td):
    logger.info("Grouping by window")

    # Window
    w = F.window(
        timeColumn="_tstamp",
        windowDuration=td,  # window duration
        slideDuration=td,  # sampling frequency
    )

    # Build arguments
    args = []
    for col, m in METRICS.items():
        args += [m["func"](*m["args"]).alias(f"{col}")]

    dfa = df.groupby([w] + ["symbol"]).agg(*args)

    return dfa


# --------------------------------------------------------------------------- #
# Execute                                                                     #
# --------------------------------------------------------------------------- #

for td in [
    ("4 hours", "4h"),
    ("1 day", "1d"),
]:
    wrapper = define_table(*td)
    df = dlt.get_df(wrapper)
    display(df)
