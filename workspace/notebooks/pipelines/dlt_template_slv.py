# Databricks notebook source
# MAGIC %pip install laktory

# COMMAND ----------
import pyspark.sql.functions as F

from laktory import dlt
from laktory import models
from laktory import read_metadata
from laktory import settings
from laktory import get_logger

dlt.spark = spark
logger = get_logger(__name__)


# Read pipeline definition
pl_name = spark.conf.get("pipeline_name", "pl-stock-prices")
pl = read_metadata(pipeline=pl_name)


def define_silver_table(table):
    @dlt.table(
        name=table.name,
        comment=table.comment,
    )
    def get_df():
        logger.info(f"Building {table.name} table")

        # Read Source
        df = table.read_source(spark)
        df.printSchema()

        # Process
        df = table.process_silver(df, table)

        # Return
        return df

    return get_df


# Build tables
for table in pl.tables:
    if table.zone == "SILVER":
        wrapper = define_silver_table(table)
        df = dlt.get_df(wrapper)
        display(df)
