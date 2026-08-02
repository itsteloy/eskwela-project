import sqlite3

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

# SQL statement to delete all data from a table named 'employees'
sql_delete_query = "DELETE FROM auth_user WHERE id IN (25, 26);"

cursor.execute(sql_delete_query)

# Commit the changes to the database
conn.commit()

# Close the connection
conn.close()
