import pickle
from typing import Any
import asyncio
from asyncio.mixins import _LoopBoundMixin
from dataclasses import dataclass

class Connection:
	def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
		self._reader = reader
		self._writer = writer

	@property
	def _connected(self) -> bool:
		return self._reader is not None

	@property
	def connected(self) -> bool:
		return self._connected

	async def close(self):
		if not self._connected:
			return
		
		self._reader = None
		self._writer.close()
		await self._writer.wait_closed()
		self._writer = None

	async def __aexit__(self, *args):
		await self.close()

	def is_active(self) -> bool:
		if not self._connected or self._reader.at_eof(): #not sure about eof
			return False
		return True

	async def send(self, obj: Any, drain_immediately=True) -> bool:
		data = pickle.dumps(obj)

		try:
			self._writer.write(len(data).to_bytes(4, 'big'))
			self._writer.write(data)

			if drain_immediately:
				await self._writer.drain()
		except Exception:
			pass
		
		return True
	
	#At most waits 2 * timeout, timeout in seconds
	async def read(self, on_exception=Exception, *, timeout: float = None) -> Any:
		try:
			len = int.from_bytes(await asyncio.wait_for(self._reader.readexactly(4), timeout), 'big')
			return pickle.loads(await asyncio.wait_for(self._reader.readexactly(len), timeout))
		except Exception:
			if on_exception == Exception:
				raise
			return on_exception
	
	def __del__(self): #to remove stupid mistakes
		assert not self._connected

class Client(Connection):
	def __init__(self, port: int):
		super().__init__(None, None)
		self._port = port
	
	async def connect(self) -> bool:
		if self._connected:
			return True

		try:
			super().__init__(*await asyncio.open_connection('127.0.0.1', self._port))
			return True
		except Exception:
			return False

	async def __aenter__(self):
		await self.connect()
		return self

class FuncCall:
	name: str
	args: list[Any]
	kwargs: dict[str, Any]

	def __init__(self, name: str, *args, **kwargs):
		self.name = name
		self.args = args
		self.kwargs = kwargs

	async def apply(self, f, *args, **kwargs):
		return await f(*args, *self.args, **kwargs, **self.kwargs)

@dataclass
class Packet:
	id: int
	data: Any

class FuncConnection(_LoopBoundMixin):
	last_id: int = 0
	_read_lock: bool
	_waiters: dict[int, asyncio.Future]
	_ready: dict[int, Any]

	def __init__(self, conn: Connection):
		self._conn = conn
		self._read_lock = asyncio.Lock()
		self._waiters = {}
		self._ready = {}

	@staticmethod
	def __generate_id():
		result = FuncConnection.last_id
		FuncConnection.last_id += 1
		return result

	def _wake_up(self, id: int, data: Any):
		if id not in self._waiters:
			self._ready[id] = data
			return
		
		fut = self._waiters[id]
		if not fut.done():
			fut.set_result(data)
	
	def _set_exception(self, exc: Exception):
		for k, v in self._waiters.items():
			v.set_exception(exc)

	async def _read(self, on_exception: Any, my_id: int):
		async with self._read_lock:
			try:
				packet: Packet = await self._conn.read()
			except Exception as e:
				self._set_exception(e)
				if on_exception == Exception:
					raise
				return on_exception

		self._wake_up(packet.id, packet.data)

		if my_id in self._ready:
			return self._ready.pop(my_id)
		
		fut = self._get_loop().create_future()
		self._waiters[my_id] = fut

		try:
			data = await fut
		except Exception:
			if on_exception == Exception:
				raise
			return on_exception
		finally:
			self._waiters.pop(my_id)
		
		return data
	
	async def _send(self, data: Any, id: int = None) -> int:
		if id is None:
			id = self.__generate_id()
		await self._conn.send(Packet(id, data))
		return id

	async def call_func(self, func: FuncCall, on_exception: Any=Exception) -> Any:
		id = await self._send(func)
		return await self._read(on_exception, id)

	async def call(self, on_exception: Any, func: str, *args, **kwargs) -> Any:
		return await self.call_func(FuncCall(func, *args, **kwargs), on_exception)

class Response(Packet):
	_conn: Connection

	def __init__(self, conn: Connection, packet: Packet):
		Packet.__init__(self, packet.id, packet.data)
		self._conn = conn

	async def respond(self, data: Any):
		assert self.id is not None, 'alerady responded'
		await self._conn.send(Packet(self.id, data))
		self.id = None

class FuncClient(Client, FuncConnection):
	def __init__(self, port: int):
		super().__init__(port)
		FuncConnection.__init__(self, self)


class Server:
	# exception_handler accepts async callback with exception, by default stops server
	def __init__(self, port: int, connection_class=Connection, exception_handler=None):
		self._port = port
		self._connection_class = connection_class
		self._exception_handler = exception_handler
		self._exception = None
		self._server = None
		self._closed = False
		self._connections = set()
		self._connection_handlers = set()
		self._on_close = asyncio.Event()

	async def __handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
		new_connection = self._connection_class(reader, writer)
		
		try:
			self.connections.add(new_connection)
			for handle in self._connection_handlers:
				await handle(new_connection)
		except Exception as exc:
			if self._exception_handler is None:
				self._exception = exc
				await self.close()
			else:
				await self._exception_handler(exc)
		finally:
			await new_connection.close()
			self.connections.remove(new_connection)

	def on_connect(self, coro):
		if not asyncio.iscoroutinefunction(coro):
			raise TypeError('@on_connect must register a coroutine function')

		if coro.__code__.co_argcount not in [1, 2]:
			raise TypeError('@on_connect coroutines must allow for a Link argument')

		self._connection_handlers.add(coro)
		return coro

	def add_connection_handler(self, coro):
		self.on_connect(coro)

	def remove_connection_handler(self, coro):
		self._connection_handlers.discard(coro)

	def is_closed(self):
		return self._closed

	@property
	def connections(self):
		return self._connections

	async def start(self):
		if self._server is None:
			self._server = await asyncio.start_server(self.__handle_connection, '127.0.0.1', self._port)

	async def run(self):
		await self.start()
		await self._on_close.wait()

		if self._exception is not None:
			raise self._exception

	async def close(self):
		if self._closed:
			return
		self._closed = True

		for connection in list(self.connections):
			await connection.close()
		
		self._server.close()
		self._on_close.set()