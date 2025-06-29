from datetime import datetime

import narwhals as nw

import laktory as lk


@lk.api.register_anyframe_namespace("lake")
class LakeDataFrameNamespace:
    def __init__(self, _df):
        self._df = _df

    def with_last_modified(self):
        return self._df.with_columns(last_modified=nw.lit(datetime.now()))

@lk.api.register_expr_namespace("lake")
class LakeExprNamespace:
    def __init__(self, _expr):
        self._expr = _expr

    def symbol_to_name(self):
        return (
            self._expr
            .str.replace_all("AAPL", "Apple")
            .str.replace_all("GOOGL", "Google")
            .str.replace_all("MSFT", "Microsoft")
            .str.replace_all("AMZN", "Amazon")
        )

