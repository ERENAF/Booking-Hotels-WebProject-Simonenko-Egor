import sqlite3

con = sqlite3.connect("instance/booking.db")
rows = con.execute(
    "EXPLAIN QUERY PLAN SELECT * FROM bookings WHERE room_id = 5"
).fetchall()
for row in rows:
    print(row)
