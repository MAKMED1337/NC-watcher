PORT = 2000



from helper.IPC import Client # noqa: E402
import traceback # noqa: E402

class ReporterClient(Client):
	def __init__(self):
		super().__init__(PORT)

	async def report(self, message: str):
		print(message)
		await self.send(message)
	
	async def report_exception(self, exc: Exception):
		await self.report(''.join(traceback.format_exception(exc)))
	
	async def report_exc(self):
		await self.report(traceback.format_exc())