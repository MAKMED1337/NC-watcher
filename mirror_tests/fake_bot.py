import helper.db_config as config

class FakeBot:
	messages: dict[int, list[str]]

	async def send_message(self, tg_id: int, text: str):
		assert isinstance(tg_id, int) and isinstance(text, str)
		assert len(text) < 4096

		self.messages[tg_id].append(text)

	#TODO add more methods

config.bot = FakeBot()