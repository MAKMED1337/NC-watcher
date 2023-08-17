import asyncio
import pickle
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Generic, Self, TypeVar, no_type_check


class Connection:
    _reader: asyncio.StreamReader | None
    _writer: asyncio.StreamWriter | None

    def __init__(self, reader: asyncio.StreamReader | None, writer: asyncio.StreamWriter | None):
        self._reader = reader
        self._writer = writer

    @property
    def _connected(self) -> bool:
        return self._reader is not None and self._writer is not None

    @property
    def connected(self) -> bool:
        return self._connected

    @no_type_check  # mypy false alarm on reader/writer is none
    async def close(self) -> None:
        if not self._connected:
            return

        self._reader = None
        with suppress(Exception):
            await self._writer.drain()
            self._writer.close()
            await self._writer.wait_closed()
        self._writer = None

    async def __aexit__(self, *_) -> None:
        await self.close()

    @no_type_check  # mypy false alarm on reader/writer is none
    def is_active(self) -> bool:
        if not self._connected or self._reader.at_eof(): # not sure about eof
            return False
        return True

    @no_type_check  # mypy false alarm on reader/writer is none
    async def send(self, obj: Any, drain_immediately: bool = True) -> None:
        if not self._connected:
            return

        data = pickle.dumps(obj)
        with suppress(Exception):
            self._writer.write(len(data).to_bytes(4, 'big'))
            self._writer.write(data)

            if drain_immediately:
                await self._writer.drain()

    # At most waits 2 * timeout, timeout in seconds
    @no_type_check  # mypy false alarm on reader/writer is none
    async def read(self, on_exception: Any = Exception, *, timeout: float | None = None) -> Any:
        try:
            length = int.from_bytes(await asyncio.wait_for(self._reader.readexactly(4), timeout), 'big')
            return pickle.loads(await asyncio.wait_for(self._reader.readexactly(length), timeout))
        except Exception:  # noqa: BLE001
            if on_exception == Exception:
                raise
            return on_exception

    @no_type_check  # mypy false alarm on reader/writer is none
    def __del__(self):
        if self._connected:
            with suppress(Exception):
                self._writer.close()  # probably unsafe, but better than assert False


class Client(Connection):
    def __init__(self, port: int) -> None:
        self._port = port
        super().__init__(None, None)

    async def connect(self) -> bool:
        if self._connected:
            return True

        with suppress(Exception):
            super().__init__(*await asyncio.open_connection('127.0.0.1', self._port))
            return True
        return False

    async def __aenter__(self) -> Self:
        await self.connect()
        return self


class FuncCall:
    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    def __init__(self, name: str, *args: Any, **kwargs: Any):
        self.name = name
        self.args = args
        self.kwargs = kwargs

    async def apply(self, f: Callable, *args: Any, **kwargs: Any) -> Any:
        return await f(*args, *self.args, **kwargs, **self.kwargs)


@dataclass
class Packet:
    id: int
    data: Any


class FuncConnection:
    last_id: int = 0
    _read_lock: asyncio.Lock
    _waiters: dict[int, asyncio.Future]
    _ready: dict[int, Any]

    def __init__(self, conn: Connection):
        self._conn = conn
        self._read_lock = asyncio.Lock()
        self._waiters = {}
        self._ready = {}

    @staticmethod
    def __generate_id() -> int:
        result = FuncConnection.last_id
        FuncConnection.last_id += 1
        return result

    def _wake_up(self, id: int, data: Any) -> None:
        if id not in self._waiters:
            self._ready[id] = data
            return

        fut = self._waiters[id]
        if not fut.done():
            fut.set_result(data)

    def _set_exception(self, exc: Exception) -> None:
        for _k, v in self._waiters.items():
            v.set_exception(exc)

    async def _read(self, on_exception: Any, my_id: int) -> Any:
        async with self._read_lock:
            try:
                packet: Packet = await self._conn.read()
            except Exception as e:  # noqa: BLE001
                self._set_exception(e)
                if on_exception == Exception:
                    raise
                return on_exception

        self._wake_up(packet.id, packet.data)

        if my_id in self._ready:
            return self._ready.pop(my_id)

        fut = asyncio.get_event_loop().create_future()
        self._waiters[my_id] = fut

        try:
            data = await fut
        except Exception:  # noqa: BLE001
            if on_exception == Exception:
                raise
            return on_exception
        finally:
            self._waiters.pop(my_id)

        return data

    async def _send(self, data: Any, id: int | None = None) -> int:
        if id is None:
            id = self.__generate_id()
        await self._conn.send(Packet(id, data))
        return id

    async def call_func(self, func: FuncCall, on_exception: Any=Exception) -> Any:
        id = await self._send(func)
        return await self._read(on_exception, id)

    async def call(self, on_exception: Any, func: str, *args: Any, **kwargs: Any) -> Any:
        return await self.call_func(FuncCall(func, *args, **kwargs), on_exception)


class Response(Packet):
    _conn: Connection

    def __init__(self, conn: Connection, packet: Packet):
        Packet.__init__(self, packet.id, packet.data)
        self._conn = conn

    async def respond(self, data: Any) -> None:
        assert self.id != -1, 'alerady responded'
        await self._conn.send(Packet(self.id, data))
        self.id = -1


class FuncClient(Client, FuncConnection):
    def __init__(self, port: int):
        super().__init__(port)
        FuncConnection.__init__(self, self)


T = TypeVar('T', bound=Connection)
class Server(Generic[T]):
    _connections: set[T]
    _connection_handlers: set[Callable[[T], Awaitable]]
    _server: asyncio.Server | None
    _exception: Exception | None

    # exception_handler accepts async callback with exception, by default stops server
    def __init__(
            self,
            port: int,
            connection_class: type[T] = Connection,
            exception_handler: Callable[[Exception], Any] | None = None):
        self._port = port
        self._connection_class = connection_class
        self._exception_handler = exception_handler
        self._exception = None
        self._server = None
        self._closed = False
        self._connections = set()
        self._connection_handlers = set()
        self._on_close = asyncio.Event()

    async def __handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        new_connection = self._connection_class(reader, writer)

        try:
            self._connections.add(new_connection)
            for handle in self._connection_handlers:
                await handle(new_connection)
        except Exception as exc:  # noqa: BLE001
            if self._exception_handler is None:
                self._exception = exc
                await self.close()
            else:
                await self._exception_handler(exc)
        finally:
            await new_connection.close()
            self._connections.remove(new_connection)

    def on_connect(self, coro: Callable[[T], Awaitable]) -> Callable[[T], Awaitable]:
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('@on_connect must register a coroutine function')

        if coro.__code__.co_argcount not in [1, 2]:
            raise TypeError('@on_connect coroutines must allow for a Link argument')

        self._connection_handlers.add(coro)
        return coro

    def add_connection_handler(self, coro: Callable[[T], Awaitable]) -> None:
        self.on_connect(coro)

    def remove_connection_handler(self, coro: Callable[[T], Awaitable]) -> None:
        self._connection_handlers.discard(coro)

    def is_closed(self) -> bool:
        return self._closed

    @property
    def connections(self) -> set:
        return self._connections

    async def start(self) -> None:
        if self._server is None:
            self._server = await asyncio.start_server(self.__handle_connection, '127.0.0.1', self._port)

    async def run(self) -> None:
        await self.start()
        await self._on_close.wait()

        if self._exception is not None:
            raise self._exception

    async def close(self) -> None:
        if self._closed or not self._server:
            return
        self._closed = True

        for connection in list(self.connections):
            await connection.close()

        self._server.close()
        self._on_close.set()
