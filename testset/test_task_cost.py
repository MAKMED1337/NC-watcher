from testset.fake_accounts_client import *
from watcher.actions import *
from watcher.unpaid_rewards import UnpaidRewards
import pytest

pillar_iter = 0
def create_pillar_exercises(exercises_count: int):
	global pillar_iter
	pillar_iter += 1
	return Pillar({'pillar_id': pillar_iter, 'exercises': [0] * exercises_count})

def create_task(mode: int, quality: int, status: int,
	pillar: Pillar | None, resubmits: int, reward: int, ideas: list[dict] | None) -> Info: 

	return Info(mode, 0, 2, quality, status, pillar, resubmits, reward, [], ideas or [])

@pytest.mark.asyncio
async def test_AC_GQ2OS():
	pillar = create_pillar_exercises(10)
	info = create_task(18, 1, 2, pillar, 0, 740, [])
	account = FakeSingleAccount([info])

	r = await Task.load(account, (await account.get_task_list(info.mode))[0])
	assert feq(r.calculate_cost(), 740) #raw cost

	reward = UnpaidRewards(cost=1017, coef=1.1, action=ActionEnum.task, adjustment=1)
	assert r.is_same(reward) #GQ -> OS

@pytest.mark.asyncio
async def test_bugged_task(): #appears in list, but didn't have inner body
	pillar = create_pillar_exercises(0)
	info = create_task(18, 0, 5, pillar, 0, 740, []) #random quality
	account = FakeSingleAccount([info])

	list_info = (await account.get_task_list(info.mode))[0]
	account.tasks.clear() #removing body

	r = await Task.load(account, list_info) #mustn't crash
	assert feq(r.calculate_cost(), 0)