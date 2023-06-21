from accounts.client import QueryParams
from accounts.types import *
from dataclasses import asdict, dataclass, field
import copy

task_iter = 0
def generate_task_id():
	global task_iter
	task_iter += 1
	return task_iter

def make_review(verdict: int, before_resubmit: int, mine: bool) -> Review:
	data = {'verdict': verdict, 'comment': '', 'mine': mine, 'before_resubmit': before_resubmit}
	if before_resubmit is None:
		data.pop('before_resubmit')
	return Review(data)

@dataclass
class Info:
	mode: int
	my_quality: int
	my_verdict: int
	quality: int
	status: int

	pillar: Pillar | None
	resubmits: int
	reward: int
	reviews: list[Review]
	ideas: list[dict]


	task_id: int = field(default_factory=generate_task_id)
	short_descr: str = ''
	comment: str | None = None

	def convert(self, cls):
		d = asdict(self)

		pillar = self.pillar
		d['pillar_id'] = pillar.pillar_id if pillar is not None else None

		d['nightsky_requests'] = self.ideas
		d['user_task_id'] = self.task_id

		return cls(d)

def assert_unique(a):
	assert len(set(a)) == len(a)

class FakeSingleAccount:
	tasks: list[Info] = {}

	def __init__(self, tasks: list[Info]):
		self.tasks = tasks

		assert_unique([(i.mode, i.task_id) for i in tasks])
		assert_unique([p.pillar_id for p in self._pillars()])

	def _pillars(self):
		return [i.pillar for i in self.tasks if i.pillar is not None]

	async def get_task(self, mode: int, task_id: int, params=QueryParams()) -> InnerTaskInfo | None:
		return next((i.convert(InnerTaskInfo) for i in self.tasks if i.mode == mode and i.task_id == task_id), None)

	async def get_task_list(self, mode: int, params=QueryParams()) -> list[ListTaskInfo]:
		return [i.convert(ListTaskInfo) for i in self.tasks if i.mode == mode]

	async def get_pillar(self, pillar_id: int) -> Pillar | None:
		return copy.deepcopy(next((i for i in self._pillars() if i.pillar_id == pillar_id), None))