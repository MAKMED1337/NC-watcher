import pytest

from tests.test_review import create_review
from tests.test_task import create_task
from watcher.tx_resolver import split_tx_dependent


@pytest.mark.asyncio()
async def test_review_OK():  # noqa: N802
    review = await create_review(18, 1, 1, 0, 300)
    split_tx_dependent([review]) == [review], []

@pytest.mark.asyncio()
async def test_review_bad():
    review = await create_review(18, 1, 0, 1, 300)
    split_tx_dependent([review]) == [], [review]

@pytest.mark.asyncio()
async def test_task_AC():  # noqa: N802
    task = await create_task(18, 1, 2, 10, 0, 740, [])
    split_tx_dependent([task]) == [task], []

@pytest.mark.asyncio()
async def test_task_RJ():  # noqa: N802
    task = await create_task(18, 0, 5, 10, 2, 740, [])
    split_tx_dependent([task]) == [task], []
