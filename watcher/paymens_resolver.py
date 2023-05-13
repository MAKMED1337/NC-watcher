from .unpaid_rewards import UnpaidRewards
from .actions import IAction
from .kuhn import Kuhn

def resolve_payments(actions: list[IAction], rewards: list[UnpaidRewards]) -> list[tuple[IAction, UnpaidRewards]]:
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
		
		result.append((actions[j], rewards[i]))
	return result