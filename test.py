import mysql.connector as msql
dbInfo = msql.connect(
host="localhost",
user="root",
password="tiger"
)
print(dbInfo)