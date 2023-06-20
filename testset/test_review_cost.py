from testset.fake_accounts_client import *
from watcher.actions import *
import pytest

def create_review_info(mode: int, verdict: int, final_verdict: int | None, before_resubmit: bool, reward: int) -> Info: 
	if final_verdict is None:
		status = 1
	else:
		status = 2 if final_verdict == 1 else 3
	return Info(mode=mode, my_quality=verdict, my_verdict=verdict, quality=verdict, status=status, reward=reward,
	            reviews=[make_review(verdict, before_resubmit, True)],
	            pillar=None, resubmits=0, ideas=[])

async def create_review(mode: int, verdict: int, final_verdict: int | None, before_resubmit: bool, reward: int) -> Review:
	info = create_review_info(mode, verdict, final_verdict, before_resubmit, reward)
	account = FakeSingleAccount([info])
	return await Review.load(account, (await account.get_task_list(info.mode))[0])

#my, final
@pytest.mark.asyncio
async def test_AC_AC():
	r = await create_review(18, 1, 1, 0, 300)
	assert r.has_ended()
	assert feq(r.calculate_cost(), 300)

	assert r.is_same(UnpaidRewards(cost=330, coef=1.1, action=ActionEnum.review, adjustment=1))
	assert not r.is_same(UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)) #random number

@pytest.mark.asyncio
async def test_AC_RJ():
	r = await create_review(18, 1, 0, 1, 300)
	assert r.has_ended()
	assert feq(r.calculate_cost(), 0)

@pytest.mark.asyncio
async def test_RJ_AC():
	r = await create_review(18, 0, 1, 0, 300)
	assert r.has_ended()
	assert feq(r.calculate_cost(), 0)

@pytest.mark.asyncio
async def test_RJ_RJ():
	r = await create_review(18, 0, 0, 0, 300)
	assert r.has_ended()
	assert feq(r.calculate_cost(), 300)

	assert r.is_same(UnpaidRewards(cost=330, coef=1.1, action=ActionEnum.review, adjustment=1))
	assert not r.is_same(UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)) #random number

@pytest.mark.asyncio
async def test_unended_review_AC():
	r = await create_review(18, 1, None, 0, 3500)
	assert not r.has_ended()

@pytest.mark.asyncio
async def test_unended_review_RJ():
	r = await create_review(18, 0, None, 0, 3500)
	assert not r.has_ended()
