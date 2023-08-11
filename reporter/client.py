import traceback

from helper.IPC import Client

from .config import PORT


class ReporterClient(Client):
    def __init__(self) -> None:
        super().__init__(PORT)

    async def report(self, message: str) -> None:
        print(message)
        await self.send(message)

    async def report_exception(self, exc: Exception) -> None:
        await self.report(''.join(traceback.format_exception(exc)))

    async def report_exc(self) -> None:
        await self.report(traceback.format_exc())
