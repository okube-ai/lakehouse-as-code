# Databricks notebook source
# MAGIC #%pip install git+https://github.com/okube-ai/laktory.git@sparkchain_doc
# MAGIC %pip install 'laktory==0.2.1'

# COMMAND ----------
import pyspark.sql.functions as F
import importlib
import sys
import os

from laktory import dlt
from laktory import read_metadata
from laktory import get_logger

spark.conf.set("spark.sql.session.timeZone", "UTC")
dlt.spark = spark
logger = get_logger(__name__)

# Read pipeline definition
pl_name = spark.conf.get("pipeline_name", "pl-stock-prices")
pl = read_metadata(pipeline=pl_name)

# Import User Defined Functions
sys.path.append("/Workspace/pipelines/")
udfs = []
for udf in pl.udfs:
    if udf.module_path:
        sys.path.append(os.path.abspath(udf.module_path))
    module = importlib.import_module(udf.module_name)
    udfs += [getattr(module, udf.function_name)]


# --------------------------------------------------------------------------- #
# Tables                                                                      #
# --------------------------------------------------------------------------- #


def define_table(table):
    @dlt.table(
        name=table.name,
        comment=table.comment,
    )
    def get_df():
        logger.info(f"Building {table.name} table")

        # Read Source
        df = table.builder.read_source(spark)
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

# Build tables
for table in pl.tables:
    if table.builder.template == "STOCK_PERFORMANCES":
        wrapper = define_table(table)
        df = dlt.get_df(wrapper)
        display(df)
