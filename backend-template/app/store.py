from threading import Lock

_lock = Lock()
_rooms = {}
_next_id = 1

def reset():
    global _rooms,_next_id
    _rooms = {}
    _next_id = 1

def list_rooms(room_type = None):
    with _lock:
        items = list(_rooms.values())
    if room_type is not None:
        items = [r for r in items if r["room_type"]==room_type]
    return items

def get_room(room_id):
    with _lock:
        return _rooms.get(room_id)

def create_room(data):
    global _next_id
    with _lock:
        room = {"id": _next_id, **data}
        _rooms[_next_id] = room
        _next_id+=1
        return room

def update_room(room_id, changes):
    with _lock:
        room = _rooms.get(room_id)
        if room is None:
            return None
        room.update(changes)
        return room

def delete_room(room_id):
    with _lock:
        return _rooms.pop(room_id, None) is not None
