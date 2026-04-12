from datetime import datetime
import pyspark.sql.functions as F
import narwhals as nw

import laktory as lk


@lk.api.register_anyframe_namespace("workflows")
class WorkflowsDataFrameNamespace:
    def __init__(self, _df):
        self._df = _df

    def get_sample_zones(self):

        df = self._df.to_native()

        df = (
            df
            .groupby("pickup_zip")
            .agg(
                F.sum("fare_amount").alias("total_fare")
            )
        )

        return df
