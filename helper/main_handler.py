import asyncio
import traceback
from signal import SIGINT, SIGTERM

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def _main(main, exception_handler, clean_up):
	try:
		await main()
	except asyncio.CancelledError:
		pass
	except BaseException as e:
		await exception_handler(e)
	finally:
		await clean_up()

# all functions are async
def main_handler(main, exception_handler, clean_up):
	main_task = loop.create_task(_main(main, exception_handler, clean_up))
	for signal in [SIGINT, SIGTERM]:
		loop.add_signal_handler(signal, main_task.cancel)

	try:
		loop.run_until_complete(main_task)
	except:
		traceback.print_exc()
	finally:
		loop.close()