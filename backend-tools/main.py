import sqlite3
from fastapi import FastAPI

def dbGet(query : str):
    connection = sqlite3.connect("db.sqlite3")
    cursor = connection.cursor()
    rows = cursor.execute(query).fetchall()
    connection.commit()
    return rows

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello" : "World"}

@app.get("/data")
def read_data():
    logs = dbGet("SELECT * FROM log")
    return {"logs" : logs}
