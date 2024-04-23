from laktory import models
from laktory import Dispatcher

# --------------------------------------------------------------------------- #
# Dispatcher for running workflows                                            #
# --------------------------------------------------------------------------- #

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

