from .unpaid_rewards import UnpaidRewards
from .actions import IAction, Task
from .kuhn import Kuhn
from .block_processor import coef

#matcher 1 to 1
def match_txs(actions: list[IAction], rewards: list[UnpaidRewards]) -> list[tuple[IAction, UnpaidRewards]] | None:
	n, m = len(actions), len(rewards)
	if n != m:
		return None

	G = Kuhn(n + m, n)
	for i in range(n):
		for j in range(m):
			if actions[i].is_same(rewards[j]):
				G.add_edge(i, n + j)
	
	mt = G.run()
	result = []
	for i in range(m):
		j = mt[i + n]
		if j == -1:
			return None
		
		result.append((actions[j], rewards[i]))
	return result

def split_tx_dependent(actions: list[IAction]) -> tuple[list[IAction], list[IAction]]:
	def is_dependent(action: IAction):
		return isinstance(action, Task) or action.calculate_cost() != 0
	return [i for i in actions if is_dependent(i)], [i for i in actions if not is_dependent(i)]

def reward_from_action(account_id: str, action: IAction):
	return UnpaidRewards(tx_id='NULL', account_id=account_id, cost=action.calculate_cost(), coef=coef, action=action.get_enum(), adjustment=1)

def resolve_and_create_fake_tx(account_id: str, actions: list[IAction], rewards: list[UnpaidRewards]) -> list[tuple[IAction, UnpaidRewards]] | None:
	tx_actions, free_actions = split_tx_dependent(actions) #some actions don't appear in txs
	result = match_txs(tx_actions, rewards)
	
	if result is None:
		return
	
	for action in free_actions:
		result.append((action, reward_from_action(account_id, action)))
	
	return result