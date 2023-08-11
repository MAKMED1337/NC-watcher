import asyncio
import traceback
from collections.abc import Callable
from signal import SIGINT, SIGTERM

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def _main(main: Callable[[]], exception_handler: Callable[[Exception]], clean_up: Callable[[]]) -> None:
    try:
        await main()
    except Exception as e:  # noqa: BLE001
        await exception_handler(e)
    finally:
        await clean_up()

# all functions are async
def main_handler(main: Callable[[]], exception_handler: Callable[[Exception]], clean_up: Callable[[]]) -> None:
    main_task = loop.create_task(_main(main, exception_handler, clean_up))
    for signal in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal, main_task.cancel)

    try:
        loop.run_until_complete(main_task)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    finally:
        loop.close()
