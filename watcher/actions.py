from .unpaid_rewards import UnpaidRewards, ActionEnum
from accounts.client import SingleAccountsClient, ListTaskInfo
from dataclasses import dataclass, asdict, field
from .last_task_state import LastTaskState
import copy

qualities = ['Low Quality', 'Good', 'Outstanding', '', 'Has Mistakes']
verdicts = ['Reviewed, Rejected', 'Reviewed, Accepted', 'Performed']
status_names = ['RJ', 'AC']
statuses = ['Being Fixed', 'In Review', 'Accepted', 'Rejected', 'Abandoned', 'Postponed']

deviation = 0.25
power = 1e3

@dataclass
class ModeInfo:
	name: str
	resubmits: int
	max_exercises: int = 0

	def percent(self, resubmits: int) -> int:
		assert 0 <= resubmits <= self.resubmits
		assert 40 % self.resubmits == 0
		return resubmits * 40 // self.resubmits

	def exercises_cost(self, count: int) -> int:
		count = min(count, self.max_exercises)
		prices = [(5, 0), (10, 0.3 * power), (20, 0.1 * power), (1000000, 0)]
		prev, result = 0, 0
		for cnt, cost in prices:
			result += max(min(cnt, count) - prev, 0) * cost
			prev = cnt
		return result

modes: dict[int, ModeInfo] = {
	18: ModeInfo('Sunshine / Sunset', 4),
	750: ModeInfo('Acadé', 10)
}

@dataclass
class TaskInfo(ListTaskInfo):
	pillar_id: int | None
	resubmits: int
	reward: int
	reviews: list
	comment: str | None
	ideas: list[dict] = field(default_factory=list)

	def __init__(self, list_info: ListTaskInfo, data: dict):
		for k, v in asdict(list_info).items():
			setattr(self, k, v)
		
		self.pillar_id = data.get('pillar_id', None)
		self.resubmits = data['resubmits']
		self.reward = data['reward'] + int(self.status == 3) #resubmits only updates after `work on fixing`, so we need to fake it
		self.reviews = data['reviews']
		self.comment = data['comment']
		self.ideas = data.get('nightsky_requests', [])

def feq(a: float, b: float) -> bool:
	return abs(a - b) <= 1

class IAction:
	info: TaskInfo

	@property
	def task_id(self) -> int:
		return self.info.task_id

	@staticmethod
	def is_proto(info: ListTaskInfo) -> bool:
		raise NotImplementedError
	
	@staticmethod
	def get_enum() -> ActionEnum:
		raise NotImplementedError

	def has_ended(self) -> bool:
		raise NotImplementedError
	
	def diff(self, state: LastTaskState) -> list['IAction']:
		assert state.ended == False
		raise NotImplementedError

	@staticmethod
	async def load(account: SingleAccountsClient, info: ListTaskInfo) -> 'IAction':
		raise NotImplementedError

	def is_same(self, reward: UnpaidRewards) -> bool:
		raise NotImplementedError
	
	def calculate_cost(self) -> int:
		raise NotImplementedError

class Task(IAction):
	pillar: dict

	@staticmethod
	def is_proto(info: ListTaskInfo):
		return info.my_verdict == 2

	@staticmethod
	def get_enum() -> ActionEnum:
		return ActionEnum.task

	def has_ended(self) -> bool:
		info = self.info
		return info.status in (2, 4)

	def diff(self, state: LastTaskState) -> list['Task']:
		assert state.ended == False
		resubmits = state.resubmits or 0

		res = []
		for resubmit in range(resubmits + 1, self.info.resubmits + 1):
			t = copy.deepcopy(self)
			t.info.resubmits = resubmit
			t.info.status = 3
			res.append(t)
		
		if self.info.status == 2:
			res.append(self)
		
		return res

	@staticmethod
	async def load(account: SingleAccountsClient, info: ListTaskInfo) -> 'Task':
		obj = Task()

		task_id = info.task_id
		info = TaskInfo(info, await account.get_task(info.mode, task_id))
		obj.info = info

		if info.pillar_id is not None:
			obj.pillar = await account.get_pillar(info.pillar_id)
		else:
			obj.pillar = None
		
		return obj

	def is_same(self, reward: UnpaidRewards) -> bool:
		cost = self.calculate_cost() * reward.coef
		
		if feq(cost, reward.cost):
			return True
		
		if self.info.quality != 1:
			return False
		return feq((1 + deviation) * cost, reward.cost) or feq((1 - deviation) * cost, reward.cost)

	def calculate_cost(self) -> int:
		info = self.info
		if info.status in (3, 4):
			return 0

		resubmits_coef = 1 - modes[info.mode].percent(info.resubmits) / 100
		cost = info.reward * resubmits_coef #base + resubmit

		cost += 0.4 * power * len(info.ideas) #ideas

		if self.pillar is not None:
			pillar = self.pillar
			cost += modes[info.mode].exercises_cost(len(pillar.get('exercises', []))) #exercises

		assert 0 <= info.quality <= 2
		quality_coef = 1 + deviation * (info.quality - 1)

		cost *= quality_coef #quality(LQ/OS)
		return int(cost)

class Review(IAction):
	@staticmethod
	def is_proto(info: ListTaskInfo):
		return info.my_verdict != 2

	@staticmethod
	def get_enum() -> ActionEnum:
		return ActionEnum.review
	
	def get_my_review(self) -> dict | None:
		return next((review for review in self.info.reviews if review['mine']), None)

	def has_ended(self) -> bool:
		review = self.get_my_review()
		before_resubmit = review['before_resubmit'] if review is not None else False
		return self.info.status != 1 or before_resubmit
	
	def diff(self, state: LastTaskState) -> list['Review']:
		assert state.ended == False
		return [self] if self.has_ended() else []

	@staticmethod
	async def load(account: SingleAccountsClient, info: ListTaskInfo) -> 'Review':
		obj = Review()

		task_id = info.task_id

		task = await account.get_task(info.mode, task_id)
		if task is None: #probably old accepted
			assert info.status == 2
			task = {'resubmits': 0, 'reward': 0, 'reviews': []}
		
		info = TaskInfo(info, task)
		obj.info = info

		return obj

	def is_same(self, reward: UnpaidRewards) -> bool:
		return feq(self.calculate_cost() * reward.coef, reward.cost)

	def calculate_cost(self) -> int:
		info = self.info
		for r in info.reviews:
			assert 0 <= r['before_resubmit'] <= 1

		my_verdict = info.my_verdict
		status = info.status
		review = self.get_my_review()
		
		correct_verdict = review['before_resubmit'] == 0 and status == 2
		return int(info.reward * int(my_verdict == correct_verdict))

actions: list[IAction] = [Task(), Review()]

def get_proto_by_enum(db_type: ActionEnum) -> IAction:
	for i in actions:
		if i.get_enum() == db_type:
			return i
	assert False

async def load_action_by_info(account: SingleAccountsClient, info: ListTaskInfo) -> IAction:
	for i in actions:
		if i.is_proto(info):
			return await i.load(account, info)
	assert False

def get_payment_cost(reward: UnpaidRewards) -> int:
	if reward.action is ActionEnum.task:
		return reward.cost
	
	assert 0 <= reward.adjustment <= 2
	if reward.adjustment == 0:
		return 0
	return (1 + deviation * (reward.adjustment - 1)) * reward.cost