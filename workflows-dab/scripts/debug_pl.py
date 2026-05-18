from databricks.connect import DatabricksSession

import laktory as lk

# TODO: import any custom modules that register PySpark/Narwhals namespace(s)

# --------------------------------------------------------------------------- #
# Setup                                                                       #
# --------------------------------------------------------------------------- #

pl_filepath = "../laktory/pipelines/pl-taxi-trips.yml"

# Get Remote Spark Session
# https://docs.databricks.com/aws/en/dev-tools/databricks-connect/cluster-config
spark = DatabricksSession.builder.profile("lac-dev-pat").getOrCreate()

# --------------------------------------------------------------------------- #
# Get Pipeline                                                                #
# --------------------------------------------------------------------------- #

with open(pl_filepath, "r") as fp:
    pl = lk.models.Pipeline.model_validate_yaml(fp)

pl = pl.inject_vars(
    vars={}
)

# --------------------------------------------------------------------------- #
# Execute Pipeline                                                            #
# --------------------------------------------------------------------------- #

node_name = "sample_trips"

pl.execute(write_sinks=False, selects=[node_name])

df = pl.nodes_dict[node_name].output_df.to_native()
df.show()
