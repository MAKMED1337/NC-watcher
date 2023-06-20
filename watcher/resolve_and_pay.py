from.last_task_state import LastTaskState
from .action_getter import get_updates_for_action
from .tx_resolver import resolve_and_create_fake_tx
from .actions import *
from helper.db_config import db, to_mapping
from .config import bot

async def resolve_and_pay(account_id: str, action_type: ActionEnum):
	async with db.transaction(), SingleAccountsClient(account_id) as account:
		if not account.connected:
			return

		actions, states = await get_updates_for_action(account, get_proto_by_enum(action_type))

		rewards = await UnpaidRewards.get(account_id, action_type)
		result = resolve_and_create_fake_tx(account_id, actions, rewards)
		
		if result is None or len(result) == 0:
			return

		print(account_id, action_type, '->')
		for action, reward in result:
			print(action.info, to_mapping(reward))
		
		for state in states:
			print(to_mapping(state))
		print('end')

		for action, reward in result:
			await UnpaidRewards.remove_by_tx(reward.tx_id, account_id)
		await LastTaskState.bulk_update([LastTaskState(**to_mapping(i)) for i in states])

		for action, reward in result:
			await bot.notify_payment(action, to_mapping(reward))