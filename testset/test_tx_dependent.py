from watcher.tx_resolver import split_tx_dependent
from testset.test_review import create_review
from testset.test_task import create_task
import pytest

@pytest.mark.asyncio
async def test_review_OK():
	review = await create_review(18, 1, 1, 0, 300)
	split_tx_dependent([review]) == [review], []

@pytest.mark.asyncio
async def test_review_bad():
	review = await create_review(18, 1, 0, 1, 300)
	split_tx_dependent([review]) == [], [review]

@pytest.mark.asyncio
async def test_task_AC():
	task = await create_task(18, 1, 2, 10, 0, 740, [])
	split_tx_dependent([task]) == [task], []

@pytest.mark.asyncio
async def test_task_RJ():
	task = await create_task(18, 0, 5, 10, 2, 740, [])
	split_tx_dependent([task]) == [task], []