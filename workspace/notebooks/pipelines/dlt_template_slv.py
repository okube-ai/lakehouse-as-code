# Databricks notebook source
# MAGIC %pip install 'laktory==0.0.16'

# COMMAND ----------
import pyspark.sql.functions as F
import importlib
import sys
import os

from laktory import dlt
from laktory import read_metadata
from laktory import get_logger

dlt.spark = spark
logger = get_logger(__name__)

# Read pipeline definition
pl_name = spark.conf.get("pipeline_name", "pl-stock-prices")
pl = read_metadata(pipeline=pl_name)

# Import User Defined Functions
udfs = []
for udf in pl.udfs:
    if udf.module_path:
        sys.path.append(os.path.abspath(udf.module_path))
    module = importlib.import_module(udf.module)
    udfs += [getattr(module, udf.function)]


# --------------------------------------------------------------------------- #
# Non-CDC Tables                                                              #
# --------------------------------------------------------------------------- #

def define_table(table):
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
        df = table.process_silver(df, udfs=udfs)

        # Return
        return df

    return get_df


# --------------------------------------------------------------------------- #
# CDC tables                                                                  #
# --------------------------------------------------------------------------- #

def define_cdc_table(table):

    dlt.create_streaming_table(
        name=table.name,
        comment=table.comment,
    )

    df = dlt.apply_changes(**table.apply_changes_kwargs)

    return df


# --------------------------------------------------------------------------- #
# Execution                                                                   #
# --------------------------------------------------------------------------- #

# Build tables
for table in pl.tables:
    if table.zone == "SILVER":
        if table.is_from_cdc:
            df = define_cdc_table(table)
            display(df)

        else:
            wrapper = define_table(table)
            df = dlt.get_df(wrapper)
            display(df)
