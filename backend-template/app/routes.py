from flask import Blueprint, request, jsonify
from . import store

bp = Blueprint("api", __name__)

ROOM_TYPES = {"single", "double", "suite"}

def _validate(data, partial= False):
    cleaned = {}
    if "room_number" in data or not partial:
        v = data.get("room_number")
        if not isinstance(v, str) or not v.strip():
            return None, ("room_number", "room_number must be a non-empty string")
        cleaned["room_number"] = v.strip()
    if "room_type" in data or not partial:
        v = data.get("room_type")
        if v not in ROOM_TYPES:
            return None, ("room_type", f"room_type must be one of {sorted(ROOM_TYPES)}")
        cleaned["room_type"] = v
    if "price_per_night" in data or not partial:
        v = data.get("price_per_night")
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
            return None, ("price_per_night", "price_per_night must be a number > 0")
        cleaned["price_per_night"] = float(v)
    if partial and not cleaned:
        return None, (None, "no valid fields to update")
    return cleaned, None

@bp.get("/health")
def health():
    return {"status": "ok"}, 200

@bp.post("/api/rooms")
def create_room():
    data = request.get_json(silent=True)
    if data is None:
        return {"error": "invalid JSON", "field": None}, 400
    if not isinstance(data, dict):
        return {"error": "request body must be a JSON object", "field": None}, 400
    cleaned, err = _validate(data, partial=False)
    if err:
        field, msg = err
        return {"error": msg, "field": field}, 400
    room = store.create_room(cleaned)
    return room, 201

@bp.get("/api/rooms")
def list_rooms():
    room_type = request.args.get("room_type")
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return {"error": "limit and offset must be integers", "field": None}, 400
    if limit < 0 or offset < 0:
        return {"error": "limit and offset must be >= 0", "field": None}, 400

    items = store.list_rooms(room_type=room_type)
    items = items[offset:offset + limit]
    return jsonify(items), 200

@bp.get("/api/rooms/<int:room_id>")
def get_room(room_id):
    room = store.get_room(room_id)
    if room is None:
        return {"error": "room not found", "field": None}, 404
    return room, 200

@bp.patch("/api/rooms/<int:room_id>")
def patch_room(room_id):
    data = request.get_json(silent=True)
    if data is None:
        return {"error": "invalid JSON", "field": None}, 400
    if not isinstance(data, dict):
        return {"error": "request body must be a JSON object", "field": None}, 400
    cleaned, err = _validate(data, partial=True)
    if err:
        field, msg = err
        return {"error": msg, "field": field}, 400
    room = store.update_room(room_id, cleaned)
    if room is None:
        return {"error": "room not found", "field": None}, 404
    return room, 200

@bp.delete("/api/rooms/<int:room_id>")
def delete_room(room_id):
    if not store.delete_room(room_id):
        return {"error": "room not found", "field": None}, 404
    return "", 204
