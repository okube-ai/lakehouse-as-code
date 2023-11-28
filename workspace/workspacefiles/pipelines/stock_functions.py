import pandas as pd
import pyspark.sql.functions as F
import pyspark.sql.functions as T


@F.pandas_udf(T.StringType())
def symbol_to_name(s: pd.Series) -> pd.Series:
    return s.map(
        {
            "APPL": "Apple",
            "GOOGL": "Google",
            "MSFT": "Microsoft",
            "AMZN": "Amazon",
        }
    )
