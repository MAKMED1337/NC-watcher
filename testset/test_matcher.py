from watcher.tx_resolver import match_txs
from watcher.unpaid_rewards import UnpaidRewards, ActionEnum
from watcher.actions import *
from testset.test_task import create_task
from testset.test_review import create_review
import pytest

def is_matching(actions: list[IAction], rewards: list[UnpaidRewards]) -> bool:
	return match_txs(actions, rewards) == list(zip(actions, rewards))

def test_matcher_empty():
	assert match_txs([], []) == [] #match

def test_matcher_different_size():
	assert match_txs([], [UnpaidRewards()]) is None
	assert match_txs([IAction()], []) is None
	assert match_txs([IAction(), IAction()], [UnpaidRewards()]) is None
	assert match_txs([IAction()], [UnpaidRewards(), UnpaidRewards()]) is None

@pytest.mark.asyncio
async def test_matcher_task_1_ok():
	task = await create_task(18, 1, 2, 10, 0, 740, [])

	reward = UnpaidRewards(cost=814, coef=1.1, action=ActionEnum.task, adjustment=1)
	assert is_matching([task], [reward])

	reward = UnpaidRewards(cost=1017, coef=1.1, action=ActionEnum.task, adjustment=1)
	assert is_matching([task], [reward])

@pytest.mark.asyncio
async def test_matcher_task_1_bad():
	task = await create_task(18, 1, 2, 10, 0, 740, [])
	
	assert match_txs([task], [UnpaidRewards(cost=611, coef=1.1, action=ActionEnum.task, adjustment=1)]) is None
	assert match_txs([task], [UnpaidRewards(cost=0, coef=1.1, action=ActionEnum.task, adjustment=0)]) is None
	assert match_txs([task], [UnpaidRewards(cost=1000, coef=1.1, action=ActionEnum.task, adjustment=1)]) is None

@pytest.mark.asyncio
async def test_matcher_review_1_ok():
	review = await create_review(18, 1, 1, 0, 300)
	reward = UnpaidRewards(cost=330, coef=1.1, action=ActionEnum.review, adjustment=1)
	assert is_matching([review], [reward])

	review = await create_review(18, 0, 0, 0, 300)
	reward = UnpaidRewards(cost=330, coef=1.1, action=ActionEnum.review, adjustment=1)
	assert is_matching([review], [reward])
	
@pytest.mark.asyncio
async def test_matcher_review_1_bad():
	review = await create_review(18, 1, 1, 0, 300)
	reward = UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)
	assert match_txs([review], [reward]) is None

	review = await create_review(18, 0, 0, 0, 300)
	reward = UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)
	assert match_txs([review], [reward]) is None

@pytest.mark.asyncio
async def test_matcher_review_2_ok():
	review1 = await create_review(18, 1, 1, 0, 300)
	reward1 = UnpaidRewards(cost=330, coef=1.1, action=ActionEnum.review, adjustment=1)

	review2 = await create_review(18, 0, 0, 0, 400)
	reward2 = UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)
	assert is_matching([review1, review2], [reward1, reward2])

@pytest.mark.asyncio
async def test_matcher_review_2_bad():
	review1 = await create_review(18, 1, 1, 0, 300)
	reward1 = UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)  #random number

	review2 = await create_review(18, 0, 0, 0, 400)
	reward2 = UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)
	assert match_txs([review1, review2], [reward1, reward2]) is None
