import sqlite3
import pandas as pd

# Read Excel file
info = pd.read_excel('CA District Attorney.xlsx', header=0)

# Clean up strings
# info = info.applymap(lambda x: x.strip() if isinstance(x, str) else x)
info = info.map(lambda x: x.strip() if isinstance(x, str) else x)


# Connect to SQLite
con = sqlite3.connect("contact_info.db")
cur = con.cursor()

# Create table
cur.execute("DROP TABLE IF EXISTS contact")
cur.execute("CREATE TABLE contact(County TEXT, Name TEXT, Address TEXT, Phone TEXT, Fax TEXT, Link_to_Website TEXT)")

# Insert data
contact_list = [tuple(row) for row in info.values]
cur.executemany("INSERT INTO contact VALUES (?, ?, ?, ?, ?, ?)", contact_list)

# Save and close
con.commit()
con.close()
