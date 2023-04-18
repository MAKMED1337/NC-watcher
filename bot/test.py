from .client import BotClient
from watcher.actions import Review, Task, TaskInfo
from watcher.unpaid_rewards import UnpaidRewards, ActionEnum
import asyncio
from helper.db_config import db, start as db_start
from accounts.client import ListTaskInfo

async def main():
	await db_start()
	p = BotClient()
	async with p:
		list_info = ListTaskInfo({'mode': 750, 'user_task_id': 0, 'my_quality': 0, 'my_verdict': 0, 'quality': 0, 'short_descr': 'TEST', 'status': 0})
		task_info = TaskInfo(list_info, {'resubmits': 0, 'reward': 0, 'reviews': [{'mine': True, 'comment': 'TEST'}]})

		r = Review()
		r.info = task_info

		async with db.transaction():
			await UnpaidRewards.add('TEST', 'TEST', 0, 0, ActionEnum.review, 0)
			await p.notify_payment(r, (await UnpaidRewards.get('TEST', ActionEnum.review))[0])
			await UnpaidRewards.clear('TEST')

		t = Task()
		t.info = task_info
		async with db.transaction():
			await UnpaidRewards.add('TEST', 'TEST', 0, 0, ActionEnum.task, 0)
			await p.notify_payment(r, (await UnpaidRewards.get('TEST', ActionEnum.task))[0])
			await UnpaidRewards.clear('TEST')

if __name__ == '__main__':
	asyncio.run(main())