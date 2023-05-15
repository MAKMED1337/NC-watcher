from reporter.client import ReporterClient

reporter = ReporterClient()
async def start():
	if not reporter.is_active():
		await reporter.connect()

async def report(msg: str):
	await start()
	await reporter.report(msg)

async def report_exception(exc: Exception):
	await start()
	await reporter.report_exception(exc)

async def stop_reporter():
	await reporter.close()