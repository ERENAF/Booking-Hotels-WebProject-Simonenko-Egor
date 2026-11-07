from flask import Blueprint, request, jsonify
from sqlalchemy import select
from . import db
from .models import Room, Booking
from datetime import date
bp = Blueprint("api", __name__)

ROOM_TYPES = {"single", "double", "suite"}

def _has_overlap(room_id,check_in,check_out,exclude_booking_id = None):
    stmt = select(Booking).where(
        Booking.room_id == room_id,
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    )
    if exclude_booking_id is not None:
        stmt = stmt.where(Booking.id != exclude_booking_id)
    return db.session.execute(stmt).scalars().first() is not None

def _parse_date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None

def _validate_booking(data, partial=False):
    cleaned = {}

    if "guest_name" in data or not partial:
        v = data.get("guest_name")
        if not isinstance(v, str) or not v.strip():
            return None, ("guest_name", "guest_name must be a non-empty string")
        cleaned["guest_name"] = v.strip()

    if "check_in" in data or not partial:
        check_in = _parse_date(data.get("check_in"))
        if check_in is None:
            return None, ("check_in", "check_in must be a date in YYYY-MM-DD format")
        cleaned["check_in"] = check_in

    if "check_out" in data or not partial:
        check_out = _parse_date(data.get("check_out"))
        if check_out is None:
            return None, ("check_out", "check_out must be a date in YYYY-MM-DD format")
        cleaned["check_out"] = check_out

    if partial and not cleaned:
        return None, (None, "no valid fields to update")

    if "check_in" in cleaned and "check_out" in cleaned:
        if cleaned["check_out"] <= cleaned["check_in"]:
            return None, ("check_out", "check_out must be after check_in")

    return cleaned, None

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
    if not isinstance(data,dict):
        return {"error":"request body must be a JSON object", "field":None},400

    cleaned,err = _validate(data)
    if err:
        field,msg = err
        return {"error":msg,"field":field},400

    room = Room(**cleaned)
    db.session.add(room)
    db.session.commit()
    return room.to_dict(),201

@bp.get("/api/rooms")
def list_rooms():
    room_type = request.args.get("room_type")
    q = request.args.get("q")
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return {"error": "limit and offset must be integers", "field": None}, 400
    if limit < 0 or offset < 0:
        return {"error": "limit and offset must be >= 0", "field": None}, 400

    stmt = select(Room)
    if room_type is not None:
        stmt = stmt.where(Room.room_type == room_type)
    if q:
        stmt = stmt.where(Room.room_number.ilike(f"%{q}%"))
    stmt = stmt.order_by(Room.id).offset(offset).limit(limit)

    rooms = db.session.execute(stmt).scalars().all()
    return jsonify([r.to_dict() for r in rooms]), 200

@bp.get("/api/rooms/<int:room_id>")
def get_room(room_id):
    room = db.session.get(Room,room_id)

    if room is None:
        return {"error": "room not found", "field": None}, 404
    return room.to_dict(), 200

from sqlalchemy import func, extract

@bp.get("/api/rooms/stats")
def room_stats():
    stmt = (
        select(
            extract("year", Booking.check_in).label("year"),
            extract("month", Booking.check_in).label("month"),
            func.count(Booking.id).label("bookings_count"),
            func.sum(
                func.julianday(Booking.check_out) - func.julianday(Booking.check_in)
            ).label("total_nights"),
            func.avg(
                func.julianday(Booking.check_out) - func.julianday(Booking.check_in)
            ).label("avg_nights"),
        )
        .group_by(
            extract("year", Booking.check_in),
            extract("month", Booking.check_in),
        )
        .order_by(
            extract("year", Booking.check_in),
            extract("month", Booking.check_in),
        )
    )
    rows = db.session.execute(stmt).all()
    return jsonify([
        {
            "year": int(r.year),
            "month": int(r.month),
            "bookings_count": int(r.bookings_count),
            "total_nights": float(r.total_nights or 0),
            "avg_nights": float(r.avg_nights or 0),
        }
        for r in rows
    ]), 200

@bp.patch("/api/rooms/<int:room_id>")
def patch_room(room_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "request body must be a JSON object", "field": None}, 400
    cleaned, err = _validate(data, partial=True)
    if err:
        field, msg = err
        return {"error": msg, "field": field}, 400
    room = db.session.get(Room,room_id)
    if room is None:
        return {"error": "room not found", "field": None}, 404
    for key,value in cleaned.items():
        setattr(room,key,value)
    db.session.commit()
    return room.to_dict(), 200

@bp.delete("/api/rooms/<int:room_id>")
def delete_room(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return {"error": "room not found", "field": None}, 404

    db.session.delete(room)
    db.session.commit()
    return "", 204

@bp.post("/api/rooms/<int:room_id>/bookings")
def post_booking(room_id):
    room = db.session.get(Room,room_id)

    if room is None:
        return {"error": "room not found","field":None},404

    data = request.get_json(silent=True)

    if not isinstance(data,dict):
        return {"error": "request body must be a JSON object", "field": None}, 400

    cleaned, err = _validate_booking(data)
    if err:
        field, msg = err
        return {"error": msg, "field": field}, 400

    if _has_overlap(room_id, cleaned["check_in"], cleaned["check_out"]):
        return {"error": "booking dates overlap with an existing booking", "field": "check_in"}, 409

    booking = Booking(room_id=room_id, **cleaned)
    db.session.add(booking)
    db.session.commit()
    return booking.to_dict(), 201

@bp.get("/api/bookings/<int:booking_id>")
def get_booking(booking_id):
    data = db.session.get(Booking, booking_id)

    if data is None:
        return {"error": "booking not found", "field": None}, 404

    return data.to_dict(),200

@bp.get("/api/rooms/<int:room_id>/bookings")
def list_bookings(room_id):
    room = db.session.get(Room,room_id)

    if room is None:
        return {"error": "room not found","field":None},404

    bookings = db.session.execute(
        select(Booking)
        .where(Booking.room_id == room_id)
        .order_by(Booking.check_in)
    ).scalars().all()

    return jsonify([b.to_dict() for b in bookings]),200

@bp.patch("/api/bookings/<int:booking_id>")
def patch_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        return {"error": "booking not found", "field": None}, 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {"error": "request body must be a JSON object", "field": None}, 400

    cleaned, err = _validate_booking(data, partial=True)
    if err:
        field, msg = err
        return {"error": msg, "field": field}, 400

    new_check_in = cleaned.get("check_in", booking.check_in)
    new_check_out = cleaned.get("check_out", booking.check_out)
    if new_check_out <= new_check_in:
        return {"error": "check_out must be after check_in", "field": "check_out"}, 400

    if _has_overlap(booking.room_id, new_check_in, new_check_out, exclude_booking_id=booking.id):
        return {"error": "booking dates overlap with an existing booking", "field": "check_in"}, 409

    for key, value in cleaned.items():
        setattr(booking, key, value)
    db.session.commit()
    return booking.to_dict(), 200


@bp.delete("/api/bookings/<int:booking_id>")
def delete_booking(booking_id):
    booking = db.session.get(Booking, booking_id)

    if booking is None:
        return {"error": "booking not found", "field": None}, 404

    db.session.delete(booking)
    db.session.commit()
    return "", 204
