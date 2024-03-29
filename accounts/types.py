from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class ListTaskInfo:
	mode: int
	task_id: int
	my_quality: int
	my_verdict: int
	quality: int
	short_descr: str
	status: int

	def __init__(self, data: dict):
		self.mode = data['mode']
		self.task_id = data['user_task_id']
		self.my_quality = data['my_quality']
		self.my_verdict = data['my_verdict']
		self.quality = data['quality']
		self.short_descr = data['short_descr']
		self.status = data['status']

@dataclass
class Review:
	verdict: int #0/1
	comment: str
	mine: bool
	before_resubmit: bool | None #None on your task review

	def __init__(self, data: dict):
		self.verdict = data['verdict']
		self.comment = data['comment']
		self.mine = data['mine']
		self.before_resubmit = bool(data['before_resubmit']) if 'before_resubmit' in data else None

@dataclass
class InnerTaskInfo:
	pillar_id: int | None
	resubmits: int
	reward: int
	reviews: list[Review]
	comment: str | None
	ideas: list[dict]

	def __init__(self, data: dict):
		self.pillar_id = data.get('pillar_id')
		self.resubmits = data['resubmits']
		self.reward = data['reward']
		self.reviews = [Review(r) for r in data['reviews']]
		self.comment = data['comment']
		self.ideas = data.get('nightsky_requests', [])

@dataclass
class Status:
	can_claim_review_in: datetime | None #if banned equals None
	can_claim_task_in: datetime | None #if banned equals None
	review_penalties: int | None #if banned equals None
	status: str

	@staticmethod
	def time_or_none(s: str | None) -> datetime | None :
		return  datetime.strptime(s, '%H:%M:%S') if s is not None else None

	def __init__(self, data: dict):
		self.can_claim_review_in = Status.time_or_none(data.get('can_claim_review_in'))
		self.can_claim_task_in = Status.time_or_none(data.get('can_claim_task_in'))
		self.review_penalties = data.get('review_penalties', None)
		self.status = data['status']

@dataclass
class ModMessage:
	id: int
	msg: str

	def __init__(self, data: dict):
		self.id = data['id']
		self.msg = data['msg']

@dataclass
class Chapter:
	kind: str
	#add more fields if needed

	def __init__(self, data: dict):
		self.kind = data['kind']

	def is_exercise(self) -> bool:
		return self.kind in ('Exercise', 'Problem')

@dataclass
class Pillar:
	pillar_id: int
	chapter: list[Chapter]
	#add more fields if needed

	def __init__(self, data: dict):
		self.pillar_id = data['pillar_id']
		self.chapter = [Chapter(i) for i in (data['chapter'] or [])]
	
	@property
	def num_exercises(self):
		return sum([i.is_exercise() for i in self.chapter])