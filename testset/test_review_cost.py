from testset.fake_accounts_client import *
from watcher.actions import *
import pytest

def create_review(mode: int, verdict: int, final_verdict: int, before_resubmit: bool, reward: int) -> Info: 
	status = 2 if final_verdict == 1 else 3
	return Info(mode=mode, my_quality=verdict, my_verdict=verdict, quality=verdict, status=status, reward=reward,
	            reviews=[make_review(verdict, before_resubmit, True)],
	            pillar=None, resubmits=0, ideas=[])

#my, final
@pytest.mark.asyncio
async def test_AC_AC():
	info = create_review(18, 1, 1, 0, 300)
	account = FakeSingleAccount([info])

	r = await Review.load(account, (await account.get_task_list(info.mode))[0])
	assert feq(r.calculate_cost(), 300)

@pytest.mark.asyncio
async def test_AC_RJ():
	info = create_review(18, 1, 0, 1, 300)
	account = FakeSingleAccount([info])

	r = await Review.load(account, (await account.get_task_list(info.mode))[0])
	assert feq(r.calculate_cost(), 0)

@pytest.mark.asyncio
async def test_RJ_AC():
	info = create_review(18, 0, 1, 0, 300)
	account = FakeSingleAccount([info])

	r = await Review.load(account, (await account.get_task_list(info.mode))[0])
	assert feq(r.calculate_cost(), 0)

@pytest.mark.asyncio
async def test_RJ_RJ():
	info = create_review(18, 0, 0, 0, 300)
	account = FakeSingleAccount([info])

	r = await Review.load(account, (await account.get_task_list(info.mode))[0])
	assert feq(r.calculate_cost(), 300)