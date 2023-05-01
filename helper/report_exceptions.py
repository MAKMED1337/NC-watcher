from reporter.client import ReporterClient

async def report_exception(exc: Exception):
	if not hasattr(report_exception, 'r'):
		report_exception.r = ReporterClient()
		await report_exception.r.connect()
	await report_exception.r.report_exception(exc)