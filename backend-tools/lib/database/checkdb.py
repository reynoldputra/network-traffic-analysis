from database import dbGet

data = dbGet("SELECT * FROM log")
print(data)
