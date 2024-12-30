import sys
import importlib

from databricks.connect import DatabricksSession
from laktory import models


# --------------------------------------------------------------------------- #
# Setup                                                                       #
# --------------------------------------------------------------------------- #

stack_filepath = "../stack.yaml"

spark = DatabricksSession.builder.clusterId("0827-053207-9t2qtwo8").getOrCreate()

udf_dirpath = "../workspacefiles/pipelines/"

node_name = "gld_stock_prices_by_1d"


# --------------------------------------------------------------------------- #
# Get Pipeline                                                                #
# --------------------------------------------------------------------------- #


with open(stack_filepath, "r") as fp:
    stack = models.Stack.model_validate_yaml(fp)

pl = stack.get_env("debug").resources.pipelines["dlt-stock-prices"]
# pl = stack.get_env("debug").resources.pipelines["pl-stock-prices"]


# --------------------------------------------------------------------------- #
# Read UDFs                                                                   #
# --------------------------------------------------------------------------- #

# Import User Defined Functions
udfs = []
sys.path.append(udf_dirpath)
for udf in pl.udfs:
    module = importlib.import_module(udf.module_name)
    udfs += [getattr(module, udf.function_name)]


# --------------------------------------------------------------------------- #
# Execute Pipeline                                                            #
# --------------------------------------------------------------------------- #

if node_name:
    pl.nodes_dict[node_name].execute(spark=spark, write_sinks=False, udfs=udfs)
else:
    pl.execute(spark=spark, write_sinks=False, udfs=udfs)

# --------------------------------------------------------------------------- #
# Display Results                                                             #
# --------------------------------------------------------------------------- #

df = pl.nodes_dict[node_name].output_df
df.laktory.display()
