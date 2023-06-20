from.last_task_state import LastTaskState
from .action_getter import get_updates_for_action
from .payments_matcher import match_payments
from .actions import *
from helper.db_config import db, to_mapping
from .block_processor import coef
from .config import bot

def split_tx_dependent(actions: list[IAction]) -> tuple[list[IAction], list[IAction]]:
	f = lambda i: isinstance(i, Task) or i.calculate_cost() != 0
	return [i for i in actions if f(i)], [i for i in actions if not f(i)]

def reward_from_action(account_id: str, action: IAction):
	return UnpaidRewards(tx_id='NULL', account_id=account_id, cost=action.calculate_cost(), coef=coef, action=action.get_enum(), adjustment=1)

def resolve_and_create_fake_tx(account_id: str, actions: list[IAction], rewards: list[UnpaidRewards]) -> list[tuple[IAction, UnpaidRewards]] | None:
	tx_actions, free_actions = split_tx_dependent(actions) #some actions don't appear in txs
	result = match_payments(tx_actions, rewards)
	
	if result is None:
		return
	
	for action in free_actions:
		result.append((action, reward_from_action(account_id, action)))
	
	return result

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