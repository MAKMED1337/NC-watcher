from reporter.client import ReporterClient

reporter = ReporterClient()
async def report_exception(exc: Exception):
	if not reporter.is_active():
		await reporter.connect()
	await reporter.report_exception(exc)

async def stop_reporter():
	await reporter.close()