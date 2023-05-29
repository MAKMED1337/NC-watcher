from .actions import IAction, Review, modes
from accounts.client import SingleAccountsClient
from .last_task_state import LastTaskState
import asyncio
from typing import Awaitable

#returns diff and (state if changed else None)
async def get_diff(action: Awaitable[IAction], state: LastTaskState) -> tuple[list[IAction], LastTaskState | None]:
	action: IAction = await action
	diff = action.diff(state)

	if state.ended == action.has_ended() and (isinstance(action, Review) or state.resubmits == action.info.resubmits):
		return diff, None
	
	state.ended, state.resubmits = action.has_ended(), action.info.resubmits
	return diff, state

async def get_updates_for_mode(account: SingleAccountsClient, mode: int, states: dict[int, LastTaskState], action_type: IAction) -> tuple[list[IAction], list[LastTaskState]]:
	ended_ids = set([i.task_id for i in states.values() if i.ended])
	tasks = [r for r in await account.get_task_list(mode) if r.task_id not in ended_ids]
	
	updates = []
	for info in tasks:
		if not action_type.is_proto(info):
			continue
		
		state = states.get(info.task_id, LastTaskState(account_id=account.account_id, task_id=info.task_id, ended=False))
		updates.append(get_diff(action_type.load(account, info), state))
	
	updates = await asyncio.gather(*updates)
	diff = []
	for i, _ in updates:
		diff.extend(i)
	return diff, [i[1] for i in updates if i[1] is not None]

async def get_updates_for_action(account_id: str, action: IAction) -> tuple[list[IAction], list[LastTaskState]]:
	async with SingleAccountsClient(account_id) as account:
		if not account.connected: #could be some bug/etc, doesn't mean that account DNE
			return [], []

		states = await LastTaskState.get(account_id)
		states = {i.task_id: i for i in states}

		diff = []
		new_states = []
		for r in await asyncio.gather(*[get_updates_for_mode(account, mode, states, action) for mode in modes]):
			diff.extend(r[0])
			new_states.extend(r[1])
		return diff, new_states