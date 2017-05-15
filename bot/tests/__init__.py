import os

import pytest
import datetime
import discord
import random

slow = pytest.mark.skipif(
    "NOSLOW" in os.environ,
    reason="Please remove the NOSLOW from your env to run."
)

used_ids = []

def create_unique_id() -> int:
    """
    Create a unique Discord snowflake ID for testing.
    If by chance a duplicate ID is created, the function will attempt creating another one.
    God knows what will happen if we create too many non unique IDs in the "real world".
    """

    new_id = discord.utils.time_snowflake(
        datetime.datetime.utcnow() - datetime.timedelta(
            seconds=random.randint(0, 60),
            minutes=random.randint(0, 60),
            hours=random.randint(0, 24),
        )
    )

    if new_id in used_ids:
        return create_unique_id()
    else:
        used_ids.append(new_id)

    return new_id
