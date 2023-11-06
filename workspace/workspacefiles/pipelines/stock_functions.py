import pyspark.sql.functions as F


def high(open, close):
    return F.greatest(open, close)
