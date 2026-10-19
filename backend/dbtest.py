import mysql.connector
import traceback

print("START")

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="thiran",
        database="smart_retail",
        connection_timeout=5,
        use_pure=True
    )

    print("CONNECTED")

    db.close()

    print("CLOSED")

except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()