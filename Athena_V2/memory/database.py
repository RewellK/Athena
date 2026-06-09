import sqlite3


class MemoryDB:

    def __init__(self, db_name="knowledge.db"):

        self.conn = sqlite3.connect(
            db_name
        )

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY,
            category TEXT,
            content TEXT
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS concepts(
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS definitions(
            concept TEXT PRIMARY KEY,
            meaning TEXT
        )
        """)

        self.conn.commit()

    def save_memory(
        self,
        category,
        content
    ):

        self.conn.execute(
            """
            INSERT INTO memories
            (category, content)
            VALUES (?, ?)
            """,
            (
                category,
                content
            )
        )

        self.conn.commit()

    def save_concept(
        self,
        concept
    ):

        self.conn.execute(
            """
            INSERT OR IGNORE
            INTO concepts(name)
            VALUES (?)
            """,
            (
                concept.lower(),
            )
        )

        self.conn.commit()

    def save_definition(
        self,
        concept,
        meaning
    ):

        self.conn.execute(
            """
            INSERT OR REPLACE
            INTO definitions
            (concept, meaning)
            VALUES (?, ?)
            """,
            (
                concept.lower(),
                meaning
            )
        )

        self.conn.commit()

    def get_definition(
        self,
        concept
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT meaning
            FROM definitions
            WHERE concept = ?
            """,
            (
                concept.lower(),
            )
        )

        row = cursor.fetchone()

        if row:
            return row[0]

        return None

    def list_definitions(self):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT concept,
                   meaning
            FROM definitions
            """
        )

        return cursor.fetchall()

    def extract_concepts(
        self,
        text
    ):

        words = [
            w.strip(
                ".,!?;:"
            )
            for w in text.split()
        ]

        return [
            w.lower()
            for w in words
            if len(w) > 5
        ][:3]