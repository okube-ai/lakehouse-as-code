# MAGIC #%pip install git+https://github.com/okube-ai/laktory.git@pipeline_engines
# MAGIC %pip install 'laktory==0.3.3'

# COMMAND ----------
import importlib
import sys
import os
import pyspark.sql.functions as F

from laktory import dlt
from laktory import models
from laktory import get_logger
from laktory import settings

spark.conf.set("spark.sql.session.timeZone", "UTC")
dlt.spark = spark
logger = get_logger(__name__)

# Read pipeline definition
pl_name = spark.conf.get("pipeline_name", "pl-stock-prices")
filepath = f"/Workspace{settings.workspace_laktory_root}pipelines/{pl_name}.json"
with open(filepath, "r") as fp:
    pl = models.Pipeline.model_validate_json(fp.read())


# --------------------------------------------------------------------------- #
# Tables                                                                      #
# --------------------------------------------------------------------------- #


def define_table(node):
    @dlt.table(
        name=node.name,
        comment=node.description,
    )
    def get_df():
        logger.info(f"Building {node.name} node")

        # Read Source
        df = node.source.read(spark)
        df.printSchema()

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
            (F.product(1 + F.col("gain")) - 1).alias("gain_total"),
        )

        # ------------------------------------------------------------------- #
        # Output                                                              #
        # ------------------------------------------------------------------- #

        return df

    return get_df


# --------------------------------------------------------------------------- #
# Execution                                                                   #
# --------------------------------------------------------------------------- #

# Build nodes
for node in pl.nodes:

    if node.dlt_template != "STOCK_PERFORMANCES":
        continue

    wrapper = define_table(node)
    df = dlt.get_df(wrapper)
    display(df)
