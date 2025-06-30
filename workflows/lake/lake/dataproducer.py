from typing import Literal
from typing import Union

from pydantic import BaseModel


class DataProducer(BaseModel):
    """
    Specifications on the producer of data.

    Attributes
    ----------
    name:
        Name of the data producer
    description:
        Description of the data producer
    party:
        First, second or third party
        ref.: https://blog.hubspot.com/service/first-party-data
    """

    name: str
    description: Union[str, None] = None
    party: Literal[1, 2, 3] = 1