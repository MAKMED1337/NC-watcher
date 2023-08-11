import pytest

from tests.fake_accounts_client import FakeSingleAccount, Info, make_review
from watcher.actions import Review, feq
from watcher.last_task_state import LastTaskState
from watcher.unpaid_rewards import ActionEnum, UnpaidRewards


def create_review_info(mode: int, verdict: int, final_verdict: int | None, before_resubmit: bool, reward: int) -> Info:
    status = 1 if final_verdict is None else 2 if final_verdict == 1 else 3
    return Info(mode=mode, my_quality=verdict, my_verdict=verdict, quality=verdict, status=status, reward=reward,
                reviews=[make_review(verdict, before_resubmit, True)],
                pillar=None, resubmits=0, ideas=[])


async def create_review(mode: int, verdict: int, final_verdict: int | None, before_resubmit: bool, reward: int) -> Review:
    info = create_review_info(mode, verdict, final_verdict, before_resubmit, reward)
    account = FakeSingleAccount([info])
    return await Review.load(account, (await account.get_task_list(info.mode))[0])


#my, final
@pytest.mark.asyncio()
async def test_AC_AC():  # noqa: N802
    r = await create_review(18, 1, 1, 0, 300)
    assert r.has_ended()
    assert feq(r.calculate_cost(), 300)

    assert r.is_same(UnpaidRewards(cost=330, coef=1.1, action=ActionEnum.review, adjustment=1))
    assert not r.is_same(UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)) #random number


@pytest.mark.asyncio()
async def test_AC_RJ():  # noqa: N802
    r = await create_review(18, 1, 0, 1, 300)
    assert r.has_ended()
    assert feq(r.calculate_cost(), 0)


@pytest.mark.asyncio()
async def test_RJ_AC():  # noqa: N802
    r = await create_review(18, 0, 1, 0, 300)
    assert r.has_ended()
    assert feq(r.calculate_cost(), 0)


@pytest.mark.asyncio()
async def test_RJ_RJ():  # noqa: N802
    r = await create_review(18, 0, 0, 0, 300)
    assert r.has_ended()
    assert feq(r.calculate_cost(), 300)

    assert r.is_same(UnpaidRewards(cost=330, coef=1.1, action=ActionEnum.review, adjustment=1))
    assert not r.is_same(UnpaidRewards(cost=440, coef=1.1, action=ActionEnum.review, adjustment=1)) #random number


@pytest.mark.asyncio()
async def test_unended_review_AC():  # noqa: N802
    r = await create_review(18, 1, None, 0, 3500)
    assert not r.has_ended()


@pytest.mark.asyncio()
async def test_unended_review_RJ():  # noqa: N802
    r = await create_review(18, 0, None, 0, 3500)
    assert not r.has_ended()


@pytest.mark.asyncio()
async def test_verdict_after_resubmit():
    r = await create_review(18, 0, None, 1, 3500) #RJ
    diff = r.diff(LastTaskState(ended=False))
    assert len(diff) == 1
    assert diff[0].info.status == 3

    r = await create_review(18, 1, None, 1, 3500) #AC
    diff = r.diff(LastTaskState(ended=False))
    assert len(diff) == 1
    assert diff[0].info.status == 3
