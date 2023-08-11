import asyncio

from accounts.client import InnerTaskInfo, ListTaskInfo
from helper.db_config import db
from helper.db_config import start as db_start
from watcher.actions import FullTaskInfo, Review, Task
from watcher.unpaid_rewards import ActionEnum, UnpaidRewards

from .client import BotClient


async def main() -> None:
    await db_start()
    p = BotClient()
    async with p:
        list_info = ListTaskInfo({'mode': 750, 'user_task_id': 0, 'my_quality': 0, 'my_verdict': 0, 'quality': 0, 'short_descr': 'TEST', 'status': 0})
        inner_task_info = InnerTaskInfo({'resubmits': 0, 'reward': 0, 'reviews': [{'mine': True, 'comment': 'TEST', 'verdict': 0}], 'comment': 'IDK'})
        task_info = FullTaskInfo(list_info, inner_task_info)

        r = Review()
        r.info = task_info

        async with db.transaction():
            await UnpaidRewards.add('TEST', 'makmed1337.near', 0, 0, ActionEnum.review, 1)
            await p.notify_payment(r, (await UnpaidRewards.get('makmed1337.near', ActionEnum.review))[0])
            await UnpaidRewards.clear('makmed1337.near')

        t = Task()
        t.info = task_info
        async with db.transaction():
            await UnpaidRewards.add('TEST', 'makmed1337.near', 0, 0, ActionEnum.task, 0)
            await p.notify_payment(r, (await UnpaidRewards.get('makmed1337.near', ActionEnum.task))[0])
            await UnpaidRewards.clear('makmed1337.near')

if __name__ == '__main__':
    asyncio.run(main())
