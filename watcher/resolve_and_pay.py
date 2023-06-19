from.last_task_state import LastTaskState
from .action_getter import get_updates_for_action
from .paymens_resolver import resolve_payments
from .actions import *
from helper.db_config import db, to_mapping
from .block_processor import coef
from .config import bot

def split_tx_dependent(actions: list[IAction]) -> tuple[list[IAction], list[IAction]]:
	f = lambda i: isinstance(i, Task) or i.calculate_cost() != 0
	return [i for i in actions if f(i)], [i for i in actions if not f(i)]

def reward_from_action(account_id: str, action: IAction):
	return UnpaidRewards(tx_id='NULL', account_id=account_id, cost=action.calculate_cost(), coef=coef, action=action.get_enum(), adjustment=1)

async def resolve_and_pay(account_id: str, action_type: ActionEnum):
	async with db.transaction(), SingleAccountsClient(account_id) as account:
		if not account.connected:
			return

		actions, states = await get_updates_for_action(account, get_proto_by_enum(action_type))
		tx_actions, free_actions = split_tx_dependent(actions) #some actions don't appear in txs

		rewards = await UnpaidRewards.get(account_id, action_type)
		result = resolve_payments(tx_actions, rewards)
		
		if result is None:
			return

		if len(actions) == 0:
			return #nothing to print / update

		print(account_id, action_type, '->')
		for action, reward in result:
			print(action.info, to_mapping(reward))
		
		for action in free_actions:
			print(action.info, 'NULL')
		
		for state in states:
			print(to_mapping(state))
		print('end')

		for action, reward in result:
			await UnpaidRewards.remove_by_tx(reward.tx_id, account_id)
		await LastTaskState.bulk_update([LastTaskState(**to_mapping(i)) for i in states])

		for action, reward in result:
			await bot.notify_payment(action, to_mapping(reward))
		for action in free_actions:
			await bot.notify_payment(action, reward_from_action(account_id, action))