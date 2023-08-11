from reporter.client import ReporterClient

reporter = ReporterClient()
async def start() -> None:
    if not reporter.is_active():
        await reporter.connect()

async def report(msg: str) -> None:
    await start()
    await reporter.report(msg)

async def report_exception(exc: Exception) -> None:
    await start()
    await reporter.report_exception(exc)

async def stop_reporter() -> None:
    await reporter.close()
