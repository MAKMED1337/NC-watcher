from reporter.client import ReporterClient

async def exception_handler(exc: BaseException):
	if not hasattr(exception_handler, 'r'):
		exception_handler.r = ReporterClient()
		await exception_handler.r.connect()
	await exception_handler.r.report_exception(exc)