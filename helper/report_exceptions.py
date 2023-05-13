from reporter.client import ReporterClient

r = ReporterClient()
async def report_exception(exc: Exception):
	if not r.is_active():
		await r.connect()
	await r.report_exception(exc)

async def stop_reporter():
	await r.close()