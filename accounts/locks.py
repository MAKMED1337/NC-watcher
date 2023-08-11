from asyncio import Lock

locks: dict[str, Lock] = {}

def is_locked(account_id: str) -> bool:
    return locks.get(account_id, Lock()).locked()

def get_lock(account_id: str | None) -> Lock:
    return locks.setdefault(account_id, Lock())
