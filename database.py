
import sqlite3
from pathlib import Path


# ------------------------------------------
# DATABASE CONFIGURATION
# ------------------------------------------

DATABASE_NAME = (
    Path(__file__).resolve().parent / "biai_crm.db"
)

STATUSES = (
    "New",
    "Contacted",
    "Interested",
    "Paid",
    "Lost"
)


# ------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------

def connect():

    connection = sqlite3.connect(DATABASE_NAME)

    connection.row_factory = sqlite3.Row

    return connection


# ------------------------------------------
# CREATE DATABASE
# ------------------------------------------

def init_database():

    with connect() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS enquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                source TEXT,
                programme TEXT,
                status TEXT NOT NULL DEFAULT 'New',
                language TEXT,
                message TEXT NOT NULL,
                suggested_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


# ------------------------------------------
# SAVE NEW ENQUIRY
# ------------------------------------------

def save_enquiry(
    name,
    phone,
    source,
    programme,
    status,
    language,
    message,
    suggested_reply
):

    if status not in STATUSES:
        raise ValueError("Invalid enquiry status.")

    with connect() as connection:

        cursor = connection.execute("""
            INSERT INTO enquiries (
                name,
                phone,
                source,
                programme,
                status,
                language,
                message,
                suggested_reply
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            phone,
            source,
            programme,
            status,
            language,
            message,
            suggested_reply
        ))

        return cursor.lastrowid


# ------------------------------------------
# READ ALL ENQUIRIES
# ------------------------------------------

def get_all_enquiries():

    with connect() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM enquiries
            ORDER BY id DESC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ------------------------------------------
# UPDATE ENQUIRY STAGE
# ------------------------------------------

def update_enquiry_status(enquiry_id, new_status):

    if new_status not in STATUSES:
        raise ValueError("Invalid enquiry status.")

    with connect() as connection:

        cursor = connection.execute(
            """
            UPDATE enquiries
            SET status = ?
            WHERE id = ?
            """,
            (new_status, enquiry_id)
        )

        return cursor.rowcount > 0


# ------------------------------------------
# EDIT CUSTOMER INFORMATION
# ------------------------------------------

def update_enquiry(
    enquiry_id,
    name,
    phone,
    source,
    programme,
    language
):

    with connect() as connection:

        cursor = connection.execute("""
            UPDATE enquiries
            SET
                name = ?,
                phone = ?,
                source = ?,
                programme = ?,
                language = ?
            WHERE id = ?
        """, (
            name,
            phone,
            source,
            programme,
            language,
            enquiry_id
        ))

        return cursor.rowcount > 0


# ------------------------------------------
# DELETE ENQUIRY
# ------------------------------------------

def delete_enquiry(enquiry_id):

    with connect() as connection:

        cursor = connection.execute(
            """
            DELETE FROM enquiries
            WHERE id = ?
            """,
            (enquiry_id,)
        )

        return cursor.rowcount > 0


# ------------------------------------------
# DUPLICATE DETECTION
# ------------------------------------------

def matching_enquiries(phone, message):

    with connect() as connection:

        if phone:

            rows = connection.execute(
                """
                SELECT id, name
                FROM enquiries
                WHERE phone = ? AND message = ?
                """,
                (phone, message)
            ).fetchall()

        else:

            rows = connection.execute(
                """
                SELECT id, name
                FROM enquiries
                WHERE message = ?
                """,
                (message,)
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ------------------------------------------
# INITIALIZE DATABASE
# ------------------------------------------

init_database()
