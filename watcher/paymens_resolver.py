from .action_getter import get_unpaid_actions
from .unpaid_rewards import UnpaidRewards
from .actions import IAction
from .kuhn import Kuhn

async def resolve_payments(account_id: str, action: IAction) -> list[tuple[IAction, UnpaidRewards]]:
	rewards = await UnpaidRewards.get(account_id, action.get_enum())
	actions = await get_unpaid_actions(account_id, action)

	n, m = len(actions), len(rewards)
	G = Kuhn(n + m, n)
	for i in range(n):
		for j in range(m):
			if actions[i].is_same(rewards[j]):
				G.add_edge(i, n + j)
	
	mt = G.run()
	for i in range(m):
		if mt[i + n] == -1:
			return
	
	result = []
	for i in range(m):
		result.append((actions[mt[i + n]], rewards[i]))
	return result