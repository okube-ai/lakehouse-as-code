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

# --------------------------------------------------------------------------- #
# Account Balances                                                            #
# --------------------------------------------------------------------------- #


def define_table():
    table_name = f"gld_stock_performances"
    @dlt.table(
        name=table_name,
        table_properties={},
    )
    def get_df():

        logger.info(f"Building {table_name}")

        # ------------------------------------------------------------------- #
        # Read data                                                           #
        # ------------------------------------------------------------------- #

        logger.info("Reading data")

        df = dlt.read(f"{ws_env}.finance.slv_star_stock_prices")

        # ------------------------------------------------------------------- #
        # Group by stock / day                                                #
        # ------------------------------------------------------------------- #

        df = df.withColumn("date", F.date_trunc("DAY", F.col("_tstamp")))

        df = df.groupby(["symbol", "date"]).agg(
            F.first("open").alias("open"),
            F.last("close").alias("close"),
        )
        df = df.withColumn("gain", (F.col("close") - F.col("open")) / F.col("open"))

        df = df.groupby("symbol").agg(
            F.min("gain").alias("gain_min"),
            F.max("gain").alias("gain_max"),
            F.mean("gain").alias("gain_mean"),
            (F.product(1+F.col("gain"))-1).alias("gain_total"),
        )

        # ------------------------------------------------------------------- #
        # Output                                                              #
        # ------------------------------------------------------------------- #

        return df

    return get_df


# --------------------------------------------------------------------------- #
# Execute                                                                     #
# --------------------------------------------------------------------------- #

wrapper = define_table()
df = dlt.get_df(wrapper)
display(df)
