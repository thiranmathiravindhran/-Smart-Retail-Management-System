import mysql.connector
db = mysql.connector.connect(host="localhost", user="root", password="thiran", database="smart_retail")
print("MySQL Database Connected Successfully!")
db.close()
