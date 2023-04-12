from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import asyncio
import time
from .config import directory
from pydantic import BaseModel

from accounts.client import AccountsClient, SingleAccountsClient, QueryParams

app = FastAPI()
mode = 37

app.mount('/js', StaticFiles(directory=directory / 'js'), 'js')

next_claim_review_time = time.time()
@app.get('/claim_review')
async def claim_review():
	global next_claim_review_time
	now = time.time()
	
	if now >= next_claim_review_time:
		next_claim_review_time = now + 30
		async with AccountsClient() as c:
			await c.claim_review(mode, '', QueryParams(on_exception={}))
			next_claim_review_time = time.time() + 10
	
	async with AccountsClient() as c:
		return await c.get_status(mode)

@app.get('/status')
async def all_statuses():
	async with AccountsClient() as c:
		return await c.get_status(mode)

@app.get('/get_active_task/{account_id}')
async def get_active_task(account_id: str):
	async with SingleAccountsClient(account_id) as c:
		status = await c.get_status(mode)
		if 'user_task_id' not in status:
			return None
		
		task_id = status['user_task_id']
		return await c.get_task(mode, task_id)

@app.get('/get_task_all/{task_id}')
async def get_task_all(task_id: int, retries: int=1):
	async with AccountsClient() as c:
		return await c.get_task(mode, task_id, QueryParams(retries=retries))

@app.get('/get_answers/{task_id}')
async def get_answers(task_id: int, retries: int=1):
	async with AccountsClient() as c:
		tasks = await c.get_task(mode, task_id, QueryParams(retries=retries))
		res = {}
		for j in tasks.values():
			if j is None:
				continue
			
			exercises = j['nightsky_exercises']
			answers = j['nightsky_answers']
			if len(exercises) != len(answers):
				continue

			for i in range(len(exercises)):
				ii = str(i)
				res[ii] = [exercises[ii]['output'], exercises[ii]['wrong_output']][answers[ii]['answer']]
			break
		
		return res

class QueryBase(BaseModel):
	account_id: str

@app.post('/status')
async def status(q: QueryBase):
	async with SingleAccountsClient(q.account_id) as c:
		if not c.connected:
			return None
		return await c.get_status(mode)

class Task(QueryBase):
	task_id: int

@app.post('/get_task')
async def get_task(q: Task):
	async with SingleAccountsClient(q.account_id) as c:
		if not c.connected:
			return None
		return await c.get_task(mode, q.task_id)

class Pillar(QueryBase):
	pillar_id: int

@app.post('/pillar')
async def pillar(q: Pillar):
	async with SingleAccountsClient(q.account_id) as conn:
		if not conn.connected:
			return None
		return await conn.get_pillar(q.pillar_id)

@app.get('/')
async def root():
	async with AccountsClient() as c:
		return c.connected_ids