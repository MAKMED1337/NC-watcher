from .config import directory
from os.path import exists

_last_block_id: int = None
_last_block_path = f'{directory}/last_block.txt'

def get_last_block_id() -> int:
	global _last_block_id
	if _last_block_id is None and exists(_last_block_path):
		_last_block_id = int(open(_last_block_path, 'r').read())
	
	return _last_block_id

def update_last_block_id(block_id: int):
	global _last_block_id
	if _last_block_id is None or block_id > _last_block_id:
		_last_block_id = block_id
		open(_last_block_path, 'w').write(str(_last_block_id))