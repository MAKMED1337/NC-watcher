from .action_getter import get_action_updates
from .unpaid_rewards import UnpaidRewards
from .last_task_state import LastTaskState
from .actions import IAction
from .kuhn import Kuhn

async def resolve_payments(account_id: str, action: IAction) -> list[tuple[IAction, UnpaidRewards, LastTaskState]]:
	rewards = await UnpaidRewards.get(account_id, action.get_enum())
	actions, states = await get_action_updates(account_id, action)

	n, m = len(actions), len(rewards)
	if n != m:
		return []

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
			return []
		
		result.append((actions[j], rewards[i], states[j]))
	return result