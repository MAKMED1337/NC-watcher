import pytest

from accounts.types import PillarInfo
from tests.fake_accounts_client import FakeSingleAccount, Info
from watcher.actions import Task, feq
from watcher.last_task_state import LastTaskState
from watcher.unpaid_rewards import ActionEnum, UnpaidRewards

pillar_iter = 0
def create_pillar_exercises(exercises_count: int) -> PillarInfo:
    global pillar_iter
    pillar_iter += 1
    return PillarInfo({'pillar_id': pillar_iter, 'chapter': [{'kind': 'Exercise'}] * exercises_count})


def create_task_info(mode: int, quality: int, status: int, pillar: PillarInfo | None, resubmits: int, reward: int, ideas: list[dict] | None) -> Info:
    return Info(mode, 0, 2, quality, status, pillar, resubmits, reward, [], ideas or [])


async def create_task(mode: int, quality: int, status: int, exercises_count: int, resubmits: int, reward: int, ideas: list[dict] | None) -> Task:
    pillar = create_pillar_exercises(exercises_count)
    info = create_task_info(mode, quality, status, pillar, resubmits, reward, ideas)
    account = FakeSingleAccount([info])
    return await Task.load(account, (await account.get_task_list(info.mode))[0])


@pytest.mark.asyncio()
async def test_AC_GQ2OS():  # noqa: N802
    r = await create_task(18, 1, 2, 10, 0, 740, [])
    assert r.has_ended()
    assert feq(r.calculate_cost(), 740) #raw cost

    assert r.is_same(UnpaidRewards(cost=814, coef=1.1, action=ActionEnum.task, adjustment=1)) #coef
    assert r.is_same(UnpaidRewards(cost=1017, coef=1.1, action=ActionEnum.task, adjustment=1)) #coef, GQ -> OS

    assert not r.is_same(UnpaidRewards(cost=611, coef=1.1, action=ActionEnum.task, adjustment=1)) #can't be GQ -> LQ
    assert not r.is_same(UnpaidRewards(cost=0, coef=1.1, action=ActionEnum.task, adjustment=0)) #can't be RJ
    assert not r.is_same(UnpaidRewards(cost=1000, coef=1.1, action=ActionEnum.task, adjustment=1)) #random value


@pytest.mark.asyncio()
async def test_bugged_task(): #appears in list, but didn't have inner body
    pillar = create_pillar_exercises(0)
    info = create_task_info(18, 0, 5, pillar, 0, 740, []) #random quality
    account = FakeSingleAccount([info])

    list_info = (await account.get_task_list(info.mode))[0]
    account.tasks.clear() #removing body

    r = await Task.load(account, list_info) #mustn't crash
    assert feq(r.calculate_cost(), 0)


@pytest.mark.asyncio()
async def test_RJ():  # noqa: N802
    r = await create_task(18, 0, 5, 10, 2, 740, [])
    assert not r.has_ended()

    diff = r.diff(LastTaskState(ended=False, resubmits=0))
    assert len(diff) == 2

    for i in diff:
        assert feq(i.calculate_cost(), 0)


@pytest.mark.asyncio()
async def test_AC_resubmits():  # noqa: N802
    r = await create_task(18, 2, 2, 10, 1, 1110, [])
    assert r.has_ended()
    assert feq(r.calculate_cost(), 1247) #raw cost

    assert r.is_same(UnpaidRewards(cost=1372, coef=1.1, action=ActionEnum.task, adjustment=1))
    assert not r.is_same(UnpaidRewards(cost=0, coef=1.1, action=ActionEnum.task, adjustment=0))

    diff = r.diff(LastTaskState(ended=False, resubmits=0))
    assert len(diff) == 2
    assert feq(diff[0].calculate_cost(), 0)
    assert diff[1] == r


@pytest.mark.asyncio()
async def test_RJ_quality():  # noqa: N802
    r = await create_task(18, 3, 3, 10, 2, 740, [])
    assert not r.has_ended()
    assert feq(r.calculate_cost(), 0)
