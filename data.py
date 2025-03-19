import sqlite3

# Function to clear the database
def clear_database():
    conn = sqlite3.connect("call_analysis.db")
    cursor = conn.cursor()

    # Delete all records but keep the table structure
    cursor.execute("DELETE FROM call_reports;")

    # Reset auto-increment ID (optional)
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='call_reports';")

    conn.commit()
    conn.close()
    print("Database cleared successfully!")

# Run the function
clear_database()
