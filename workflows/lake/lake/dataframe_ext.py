import pyspark.sql.functions as F

import laktory as lk


@lk.api.register_anyframe_namespace("lake")
class LakeDataFrameNamespace:
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
