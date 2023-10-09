import sqlite3


def dbCreate(query : str, data = ()):
    connection = sqlite3.connect("db.sqlite3")
    cursor = connection.cursor()
    cursor.execute(query, data)
    connection.commit()

def dbInsert(query : str, value):
    connection = sqlite3.connect("db.sqlite3")
    cursor = connection.cursor()
    cursor.execute(query, value)
    connection.commit()

def dbGet(query : str):
    connection = sqlite3.connect("db.sqlite3")
    cursor = connection.cursor()
    rows = cursor.execute(query).fetchall()
    connection.commit()
    return rows

def dbGetColumn(query : str,value):
    connection = sqlite3.connect("db.sqlite3")
    cursor = connection.cursor()
    rows = cursor.execute(query,value).fetchall()
    connection.commit()
    return rows
