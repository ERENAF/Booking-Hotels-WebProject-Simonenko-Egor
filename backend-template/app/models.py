from datetime import date
from . import db

class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer,primary_key = True)
    room_number = db.Column(db.String(20),nullable = False)
    room_type = db.Column(db.String(20),nullable = False)
    price_per_night = db.Column(db.Float, nullable = False)

    bookings = db.relationship(
        "Booking",
        back_populates="room",
        cascade = "all,,delete-orphan",
        lazy="selectin"
    )

    def to_dict(self):
        return{
            "id":self.id,
            "room_number": self.room_number,
            "room_type":self.room_type,
            "price_per_night":self.price_per_night
        }

class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer,primary_key = True)
    room_id = db.Column(
        db.Integer,
        db.ForeignKey("rooms.id",ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    guest_name = db.Column(db.String(100),nullable = False)
    check_in = db.Column(db.Date,nullable= False)
    check_out = db.Column(db.Date, nullable = False)

    room = db.relationship("Room", back_populates = "bookings")

    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "guest_name": self.guest_name,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
        }
