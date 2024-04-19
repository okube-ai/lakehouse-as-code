import time
from laktory import models
from laktory import Dispatcher

from databricks.sdk import WorkspaceClient

wc = WorkspaceClient()

with open("./stack.yaml") as fp:
    stack = models.Stack.model_validate_yaml(fp)


dispatcher = Dispatcher(stack=stack)
dispatcher.get_resource_ids()
pl = dispatcher.resources["pl-stock-prices"]
job = dispatcher.resources["job-stock-prices"]

# Run pipeline
# pl.run(current_run_action="WAIT", full_refresh=False)

# Run job
job.run(current_run_action="CANCEL")


#
# # Run pipeline
# print("Running Pipeline...")
# status = wc.pipelines.start_update(pl._id)
# print("Done...")
#
#
# for i in range(5):
#     u = wc.pipelines.get_update(pipeline_id=pl._id, update_id=status.update_id)
#     time.sleep(1)
