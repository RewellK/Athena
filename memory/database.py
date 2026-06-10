import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta


class ThreadSafeCursor:
    """Cursor proxy that serializes access to the underlying SQLite cursor."""

    def __init__(self, cursor, lock):
        self._cursor = cursor
        self._lock = lock

    def execute(self, *args, **kwargs):
        with self._lock:
            self._cursor.execute(*args, **kwargs)
        return self

    def executemany(self, *args, **kwargs):
        with self._lock:
            self._cursor.executemany(*args, **kwargs)
        return self

    def fetchone(self):
        with self._lock:
            return self._cursor.fetchone()

    def fetchall(self):
        with self._lock:
            return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid


class ThreadSafeConnection:
    """SQLite connection proxy safe for Athena Desktop background threads.

    check_same_thread=False allows use across GUI/background threads.
    This proxy adds an RLock so execute/commit/fetch operations do not run
    concurrently on the same connection.
    """

    def __init__(self, connection, lock):
        self._connection = connection
        self._lock = lock

    def execute(self, *args, **kwargs):
        with self._lock:
            return ThreadSafeCursor(self._connection.execute(*args, **kwargs), self._lock)

    def executemany(self, *args, **kwargs):
        with self._lock:
            return ThreadSafeCursor(self._connection.executemany(*args, **kwargs), self._lock)

    def cursor(self):
        with self._lock:
            return ThreadSafeCursor(self._connection.cursor(), self._lock)

    def commit(self):
        with self._lock:
            self._connection.commit()

    def rollback(self):
        with self._lock:
            self._connection.rollback()

    def close(self):
        with self._lock:
            self._connection.close()

    def pragma(self, statement):
        with self._lock:
            self._connection.execute(statement)


class MemoryDB:

    def __init__(self, db_name="knowledge.db"):
        self.db_name = db_name
        self._lock = threading.RLock()
        parent = os.path.dirname(os.path.abspath(db_name))
        if parent:
            os.makedirs(parent, exist_ok=True)
        raw_connection = sqlite3.connect(
            db_name,
            check_same_thread=False,
            timeout=30,
            isolation_level=None,
        )
        self.conn = ThreadSafeConnection(raw_connection, self._lock)
        self._configure_connection()
        self.create_tables()

    def _configure_connection(self):
        self.conn.pragma("PRAGMA journal_mode=WAL")
        self.conn.pragma("PRAGMA synchronous=NORMAL")
        self.conn.pragma("PRAGMA busy_timeout=30000")
        self.conn.pragma("PRAGMA foreign_keys=ON")

    def close(self):
        self.conn.close()

    def create_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY,
            category TEXT,
            content TEXT,
            created_at TEXT
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

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS relationships(
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            relation TEXT NOT NULL,
            target TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(source, relation, target)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS goals(
            id INTEGER PRIMARY KEY,
            owner TEXT NOT NULL,
            goal TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(owner, goal)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            event_date TEXT,
            description TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(name, event_date)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS event_participants(
            id INTEGER PRIMARY KEY,
            event_id INTEGER NOT NULL,
            person TEXT NOT NULL,
            role TEXT NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(id),
            UNIQUE(event_id, person, role)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_decisions(
            id INTEGER PRIMARY KEY,
            input_text TEXT NOT NULL,
            action TEXT NOT NULL,
            category TEXT,
            score INTEGER NOT NULL,
            reason TEXT NOT NULL,
            saved INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS short_term_memory(
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            importance_score INTEGER NOT NULL,
            processed INTEGER NOT NULL DEFAULT 0
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS mid_term_memory(
            id INTEGER PRIMARY KEY,
            summary TEXT NOT NULL,
            topics TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            importance_score INTEGER NOT NULL,
            promoted INTEGER NOT NULL DEFAULT 0,
            UNIQUE(summary)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_promotions(
            id INTEGER PRIMARY KEY,
            source_layer TEXT NOT NULL,
            target_layer TEXT NOT NULL,
            content TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)



        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS entities(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            entity_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS world_relationships(
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            relation TEXT NOT NULL,
            target TEXT NOT NULL,
            confidence INTEGER NOT NULL DEFAULT 80,
            created_at TEXT NOT NULL,
            UNIQUE(source, relation, target)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS world_events(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            date TEXT,
            description TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(name, event_type, date)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS world_event_participants(
            id INTEGER PRIMARY KEY,
            event_id INTEGER NOT NULL,
            person TEXT NOT NULL,
            role TEXT NOT NULL,
            FOREIGN KEY(event_id) REFERENCES world_events(id),
            UNIQUE(event_id, person, role)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_states(
            id INTEGER PRIMARY KEY,
            entity_name TEXT NOT NULL,
            attribute TEXT NOT NULL,
            value TEXT NOT NULL,
            source_event TEXT,
            confidence INTEGER NOT NULL DEFAULT 80,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(entity_name, attribute)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memory(
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            source TEXT,
            importance_score INTEGER NOT NULL DEFAULT 80,
            created_at TEXT NOT NULL
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS world_extractions(
            id INTEGER PRIMARY KEY,
            input_text TEXT NOT NULL,
            proposed_json TEXT NOT NULL,
            saved_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS reasoning_conclusions(
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL,
            statement TEXT NOT NULL,
            confidence REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            origin TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(category, statement, origin)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_sources(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            origin TEXT NOT NULL,
            confidence REAL NOT NULL,
            rationale TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_ingestions(
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            summary TEXT,
            extracted_json TEXT NOT NULL,
            saved_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES knowledge_sources(id)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_source_items(
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            statement TEXT NOT NULL,
            confidence REAL NOT NULL,
            origin TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES knowledge_sources(id),
            UNIQUE(source_id, category, statement)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS intentions(
            id INTEGER PRIMARY KEY,
            source_text TEXT NOT NULL,
            intention_json TEXT NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS agency_goals(
            id INTEGER PRIMARY KEY,
            intention_id INTEGER,
            description TEXT NOT NULL,
            rationale TEXT,
            priority REAL NOT NULL DEFAULT 0.5,
            confidence REAL NOT NULL DEFAULT 0.5,
            status TEXT NOT NULL DEFAULT 'proposed',
            created_at TEXT NOT NULL,
            FOREIGN KEY(intention_id) REFERENCES intentions(id)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS plans(
            id INTEGER PRIMARY KEY,
            goal_id INTEGER,
            plan_json TEXT NOT NULL,
            status TEXT NOT NULL,
            requires_approval INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY(goal_id) REFERENCES agency_goals(id)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS tool_registry(
            id TEXT PRIMARY KEY,
            capability TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            cost REAL NOT NULL DEFAULT 0.0,
            latency REAL NOT NULL DEFAULT 0.0,
            last_used TEXT,
            success_rate REAL NOT NULL DEFAULT 0.5,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS actions(
            id INTEGER PRIMARY KEY,
            plan_id INTEGER,
            tool_id TEXT,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            approval_required INTEGER NOT NULL DEFAULT 1,
            result_summary TEXT,
            created_at TEXT NOT NULL,
            executed_at TEXT,
            FOREIGN KEY(plan_id) REFERENCES plans(id),
            FOREIGN KEY(tool_id) REFERENCES tool_registry(id)
        )
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS outcomes(
            id INTEGER PRIMARY KEY,
            action_id INTEGER,
            status TEXT NOT NULL,
            summary TEXT NOT NULL,
            reflection TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(action_id) REFERENCES actions(id)
        )
        """)

        self.conn.commit()

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def _hash(self, content):
        return hashlib.sha256(content.strip().lower().encode("utf-8")).hexdigest()

    def save_memory(self, category, content):
        self.conn.execute(
            """
            INSERT INTO memories(category, content, created_at)
            VALUES (?, ?, ?)
            """,
            (category, content, self._now())
        )
        self.conn.commit()

    def list_memories(self, category=None, created_at_prefix=None):
        query = "SELECT category, content, created_at FROM memories WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if created_at_prefix:
            query += " AND created_at LIKE ?"
            params.append(f"{created_at_prefix}%")

        query += " ORDER BY created_at ASC"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def count_memories(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        return cursor.fetchone()[0]

    def save_concept(self, concept):
        self.conn.execute("INSERT OR IGNORE INTO concepts(name) VALUES (?)", (concept.lower().strip(),))
        self.conn.commit()

    def list_concepts(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM concepts ORDER BY name")
        return cursor.fetchall()

    def save_definition(self, concept, meaning):
        self.conn.execute(
            "INSERT OR REPLACE INTO definitions(concept, meaning) VALUES (?, ?)",
            (concept.lower().strip(), meaning.strip())
        )
        self.conn.commit()

    def get_definition(self, concept):
        cursor = self.conn.cursor()
        cursor.execute("SELECT meaning FROM definitions WHERE concept = ?", (concept.lower().strip(),))
        row = cursor.fetchone()
        return row[0] if row else None

    def list_definitions(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT concept, meaning FROM definitions ORDER BY concept")
        return cursor.fetchall()

    def save_relationship(self, source, relation, target):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO relationships(source, relation, target, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (source.strip(), relation.strip().lower(), target.strip(), self._now())
        )
        self.conn.commit()

    def find_relationships(self, source=None, relation=None, target=None):
        query = "SELECT source, relation, target, created_at FROM relationships WHERE 1=1"
        params = []
        if source:
            query += " AND lower(source) = lower(?)"
            params.append(source.strip())
        if relation:
            query += " AND relation = ?"
            params.append(relation.strip().lower())
        if target:
            query += " AND lower(target) = lower(?)"
            params.append(target.strip())
        query += " ORDER BY created_at ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def list_relationships(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT source, relation, target, created_at FROM relationships ORDER BY created_at ASC")
        return cursor.fetchall()

    def save_goal(self, owner, goal, status="active", priority="medium"):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO goals(owner, goal, status, priority, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (owner.strip(), goal.strip(), status.strip(), priority.strip(), self._now())
        )
        self.conn.commit()

    def list_goals(self, owner=None, status=None):
        query = "SELECT owner, goal, status, priority, created_at FROM goals WHERE 1=1"
        params = []
        if owner:
            query += " AND lower(owner) = lower(?)"
            params.append(owner.strip())
        if status:
            query += " AND lower(status) = lower(?)"
            params.append(status.strip())
        query += " ORDER BY created_at ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def save_event(self, name, event_date=None, description=""):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO events(name, event_date, description, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name.strip(), event_date, description.strip(), self._now())
        )
        self.conn.commit()
        cursor.execute(
            """
            SELECT id FROM events
            WHERE lower(name) = lower(?)
            AND (event_date = ? OR (event_date IS NULL AND ? IS NULL))
            """,
            (name.strip(), event_date, event_date)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def list_events(self, month=None):
        query = "SELECT id, name, event_date, description, created_at FROM events WHERE 1=1"
        params = []
        if month:
            query += " AND event_date LIKE ?"
            params.append(f"%-{month:02d}-%")
        query += " ORDER BY event_date ASC, created_at ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def find_events_by_name(self, name_fragment):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, name, event_date, description, created_at
            FROM events
            WHERE lower(name) LIKE lower(?)
            ORDER BY event_date ASC, created_at ASC
            """,
            (f"%{name_fragment.strip()}%",)
        )
        return cursor.fetchall()

    def save_event_participant(self, event_id, person, role="participant"):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO event_participants(event_id, person, role)
            VALUES (?, ?, ?)
            """,
            (event_id, person.strip(), role.strip())
        )
        self.conn.commit()

    def list_event_participants(self, event_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT person, role FROM event_participants WHERE event_id = ? ORDER BY person ASC", (event_id,))
        return cursor.fetchall()

    def save_learning_decision(self, input_text, action, category, score, reason, saved=False):
        self.conn.execute(
            """
            INSERT INTO learning_decisions(input_text, action, category, score, reason, saved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (input_text.strip(), action, category, score, reason, 1 if saved else 0, self._now())
        )
        self.conn.commit()

    def list_learning_decisions(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT input_text, action, category, score, reason, saved, created_at
            FROM learning_decisions
            ORDER BY created_at ASC
            """
        )
        return cursor.fetchall()

    def save_short_term_memory(self, content, importance_score=0, hours_to_live=24):
        now = datetime.now()
        expires_at = now + timedelta(hours=hours_to_live)
        self.conn.execute(
            """
            INSERT OR IGNORE INTO short_term_memory(content, content_hash, created_at, expires_at, importance_score, processed)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                content.strip(),
                self._hash(content),
                now.isoformat(timespec="seconds"),
                expires_at.isoformat(timespec="seconds"),
                int(importance_score),
            )
        )
        self.conn.commit()

    def list_short_term_memory(self, include_expired=False, processed=None, created_at_prefix=None):
        query = "SELECT id, content, content_hash, created_at, expires_at, importance_score, processed FROM short_term_memory WHERE 1=1"
        params = []
        if not include_expired:
            query += " AND expires_at > ?"
            params.append(self._now())
        if processed is not None:
            query += " AND processed = ?"
            params.append(1 if processed else 0)
        if created_at_prefix:
            query += " AND created_at LIKE ?"
            params.append(f"{created_at_prefix}%")
        query += " ORDER BY created_at ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def mark_short_term_processed(self, memory_id):
        self.conn.execute("UPDATE short_term_memory SET processed = 1 WHERE id = ?", (memory_id,))
        self.conn.commit()

    def expire_short_term_memory(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM short_term_memory WHERE expires_at <= ?", (self._now(),))
        deleted = cursor.rowcount
        self.conn.commit()
        return deleted

    def save_mid_term_memory(self, summary, topics, source_count, importance_score=0, days_to_live=7):
        now = datetime.now()
        expires_at = now + timedelta(days=days_to_live)
        topics_text = json.dumps(topics, ensure_ascii=False) if isinstance(topics, list) else str(topics)
        self.conn.execute(
            """
            INSERT OR IGNORE INTO mid_term_memory(summary, topics, source_count, created_at, expires_at, importance_score, promoted)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                summary.strip(),
                topics_text,
                int(source_count),
                now.isoformat(timespec="seconds"),
                expires_at.isoformat(timespec="seconds"),
                int(importance_score),
            )
        )
        self.conn.commit()

    def list_mid_term_memory(self, include_expired=False, promoted=None):
        query = "SELECT id, summary, topics, source_count, created_at, expires_at, importance_score, promoted FROM mid_term_memory WHERE 1=1"
        params = []
        if not include_expired:
            query += " AND expires_at > ?"
            params.append(self._now())
        if promoted is not None:
            query += " AND promoted = ?"
            params.append(1 if promoted else 0)
        query += " ORDER BY importance_score DESC, source_count DESC, created_at ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def mark_mid_term_promoted(self, memory_id):
        self.conn.execute("UPDATE mid_term_memory SET promoted = 1 WHERE id = ?", (memory_id,))
        self.conn.commit()

    def expire_mid_term_memory(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM mid_term_memory WHERE expires_at <= ? AND promoted = 0", (self._now(),))
        deleted = cursor.rowcount
        self.conn.commit()
        return deleted

    def save_memory_promotion(self, source_layer, target_layer, content, reason):
        self.conn.execute(
            """
            INSERT INTO memory_promotions(source_layer, target_layer, content, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_layer, target_layer, content, reason, self._now())
        )
        self.conn.commit()

    def list_memory_promotions(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT source_layer, target_layer, content, reason, created_at
            FROM memory_promotions
            ORDER BY created_at ASC
            """
        )
        return cursor.fetchall()

    def count_short_term_memory(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM short_term_memory WHERE expires_at > ?", (self._now(),))
        return cursor.fetchone()[0]

    def count_mid_term_memory(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM mid_term_memory WHERE expires_at > ?", (self._now(),))
        return cursor.fetchone()[0]

    def count_long_term_memory(self):
        return (
            self.count_memories()
            + len(self.list_definitions())
            + len(self.list_relationships())
            + len(self.list_goals())
            + len(self.list_events())
            + self.count_real_long_term_memory()
            + self.count_entities()
            + self.count_world_relationships()
            + self.count_world_events()
            + self.count_entity_states()
            + self.count_knowledge_source_items()
        )

    def frequent_terms(self, rows, min_count=2):
        ignored = {
            "athena", "quero", "tenho", "hoje", "sobre", "minha", "meu", "para", "como",
            "você", "voce", "isso", "essa", "esse", "mais", "muito", "pouco", "dia",
            "apareceu", "memória", "memoria", "semana", "curiosa", "pretende", "esquecer",
            "quem", "qual", "quais", "quando", "onde", "conhece", "estado", "atual"
        }
        counts = {}
        for row in rows:
            content = row[1] if len(row) > 1 else str(row)
            for raw in content.replace(".", " ").replace(",", " ").replace("?", " ").split():
                word = raw.strip().lower()
                if len(word) < 4 or word in ignored:
                    continue
                counts[word] = counts.get(word, 0) + 1
        return sorted(
            [(word, count) for word, count in counts.items() if count >= min_count],
            key=lambda item: (-item[1], item[0])
        )


    # ==========================
    # WORLD MODEL V8
    # ==========================

    def save_entity(self, name, entity_type="unknown"):
        clean_name = name.strip() if name else ""
        if not clean_name:
            return None
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO entities(name, entity_type, created_at)
            VALUES (?, ?, ?)
            """,
            (clean_name, entity_type.strip().lower(), self._now())
        )
        self.conn.commit()
        cursor.execute("SELECT id FROM entities WHERE lower(name) = lower(?)", (clean_name,))
        row = cursor.fetchone()
        return row[0] if row else None

    def list_entities(self, entity_type=None):
        query = "SELECT id, name, entity_type, created_at FROM entities WHERE 1=1"
        params = []
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type.strip().lower())
        query += " ORDER BY entity_type ASC, name ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def find_entities(self, name_fragment=None, entity_type=None, limit=20):
        query = "SELECT id, name, entity_type, created_at FROM entities WHERE 1=1"
        params = []
        if name_fragment:
            query += " AND lower(name) LIKE lower(?)"
            params.append(f"%{str(name_fragment).strip()}%")
        if entity_type:
            query += " AND entity_type = ?"
            params.append(str(entity_type).strip().lower())
        query += " ORDER BY name ASC LIMIT ?"
        params.append(int(limit or 20))
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def count_entities(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        return cursor.fetchone()[0]

    def save_world_relationship(self, source, relation, target, confidence=80):
        if not source or not relation or not target:
            return
        self.conn.execute(
            """
            INSERT OR IGNORE INTO world_relationships(source, relation, target, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source.strip(), relation.strip().lower(), target.strip(), int(confidence), self._now())
        )
        self.conn.commit()

    def find_world_relationships(self, source=None, relation=None, target=None):
        query = "SELECT id, source, relation, target, confidence, created_at FROM world_relationships WHERE 1=1"
        params = []
        if source:
            query += " AND lower(source) = lower(?)"
            params.append(source.strip())
        if relation:
            query += " AND relation = ?"
            params.append(relation.strip().lower())
        if target:
            query += " AND lower(target) = lower(?)"
            params.append(target.strip())
        query += " ORDER BY created_at ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def list_world_relationships(self, source=None, relation=None, target=None):
        return self.find_world_relationships(source=source, relation=relation, target=target)

    def count_world_relationships(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM world_relationships")
        return cursor.fetchone()[0]

    def save_world_event(self, name, event_type="generic", date=None, description=""):
        if not name:
            return None
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO world_events(name, event_type, date, description, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), event_type.strip().lower(), date, description.strip(), self._now())
        )
        self.conn.commit()
        cursor.execute(
            """
            SELECT id FROM world_events
            WHERE lower(name) = lower(?) AND event_type = ? AND (date = ? OR (date IS NULL AND ? IS NULL))
            """,
            (name.strip(), event_type.strip().lower(), date, date)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def list_world_events(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, event_type, date, description, created_at FROM world_events ORDER BY date ASC, created_at ASC")
        return cursor.fetchall()

    def find_world_events(self, name_fragment=None, entity_name=None):
        query = "SELECT DISTINCT e.id, e.name, e.event_type, e.date, e.description, e.created_at FROM world_events e"
        params = []
        if entity_name:
            query += " LEFT JOIN world_event_participants p ON p.event_id = e.id"
        query += " WHERE 1=1"
        if name_fragment:
            query += " AND lower(e.name) LIKE lower(?)"
            params.append(f"%{name_fragment.strip()}%")
        if entity_name:
            query += " AND lower(p.person) = lower(?)"
            params.append(entity_name.strip())
        query += " ORDER BY e.date ASC, e.created_at ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def count_world_events(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM world_events")
        return cursor.fetchone()[0]

    def save_world_event_participant(self, event_id, person, role="participant"):
        if not event_id or not person:
            return
        self.conn.execute(
            """
            INSERT OR IGNORE INTO world_event_participants(event_id, person, role)
            VALUES (?, ?, ?)
            """,
            (event_id, person.strip(), role.strip().lower())
        )
        self.conn.commit()

    def list_world_event_participants(self, event_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT person, role FROM world_event_participants WHERE event_id = ? ORDER BY role ASC, person ASC", (event_id,))
        return cursor.fetchall()

    def save_entity_state(self, entity_name, attribute, value, source_event=None, confidence=80):
        if not entity_name or not attribute or not value:
            return
        now = self._now()
        self.conn.execute(
            """
            INSERT INTO entity_states(entity_name, attribute, value, source_event, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_name, attribute) DO UPDATE SET
                value = excluded.value,
                source_event = excluded.source_event,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at
            """,
            (entity_name.strip(), attribute.strip().lower(), value.strip(), source_event, int(confidence), now, now)
        )
        self.conn.commit()

    def get_entity_state(self, entity_name, attribute):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT entity_name, attribute, value, source_event, confidence, created_at, updated_at
            FROM entity_states
            WHERE lower(entity_name) = lower(?) AND attribute = ?
            """,
            (entity_name.strip(), attribute.strip().lower())
        )
        return cursor.fetchone()

    def list_entity_states(self, entity_name=None):
        query = "SELECT id, entity_name, attribute, value, source_event, confidence, created_at, updated_at FROM entity_states WHERE 1=1"
        params = []
        if entity_name:
            query += " AND lower(entity_name) = lower(?)"
            params.append(entity_name.strip())
        query += " ORDER BY entity_name ASC, attribute ASC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def count_entity_states(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entity_states")
        return cursor.fetchone()[0]

    def save_long_term_memory(self, content, source="manual", importance_score=80):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO long_term_memory(content, content_hash, source, importance_score, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (content.strip(), self._hash(content), source, int(importance_score), self._now())
        )
        self.conn.commit()

    def list_long_term_memory(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, content, source, importance_score, created_at FROM long_term_memory ORDER BY created_at ASC")
        return cursor.fetchall()

    def count_real_long_term_memory(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM long_term_memory")
        return cursor.fetchone()[0]

    def save_world_extraction(self, input_text, proposed, saved):
        self.conn.execute(
            """
            INSERT INTO world_extractions(input_text, proposed_json, saved_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                input_text.strip(),
                json.dumps(proposed, ensure_ascii=False),
                json.dumps(saved, ensure_ascii=False),
                self._now()
            )
        )
        self.conn.commit()

    def list_world_extractions(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT input_text, proposed_json, saved_json, created_at FROM world_extractions ORDER BY created_at ASC")
        return cursor.fetchall()


    # ==========================
    # KNOWLEDGE SOURCES V10
    # ==========================

    def save_knowledge_source(self, name, source_type="unknown", origin="unknown", confidence=0.5, rationale="", metadata=None):
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO knowledge_sources(name, source_type, origin, confidence, rationale, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (name or "fonte_sem_nome").strip(),
                (source_type or "unknown").strip(),
                (origin or "unknown").strip(),
                float(confidence),
                rationale or "",
                metadata_json,
                self._now(),
            )
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_knowledge_sources(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, name, source_type, origin, confidence, rationale, metadata_json, created_at
            FROM knowledge_sources
            ORDER BY created_at DESC
            """
        )
        return cursor.fetchall()

    def save_knowledge_ingestion(self, source_id, content, summary, extracted, saved):
        self.conn.execute(
            """
            INSERT INTO knowledge_ingestions(source_id, content, content_hash, summary, extracted_json, saved_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(source_id),
                content or "",
                self._hash(content or ""),
                summary or "",
                json.dumps(extracted or {}, ensure_ascii=False),
                json.dumps(saved or {}, ensure_ascii=False),
                self._now(),
            )
        )
        self.conn.commit()

    def list_knowledge_ingestions(self, created_at_prefix=None):
        query = """
            SELECT i.id, i.source_id, s.name, s.origin, s.confidence, i.summary, i.created_at
            FROM knowledge_ingestions i
            JOIN knowledge_sources s ON s.id = i.source_id
            WHERE 1=1
        """
        params = []
        if created_at_prefix:
            query += " AND i.created_at LIKE ?"
            params.append(f"{created_at_prefix}%")
        query += " ORDER BY i.created_at DESC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def save_knowledge_source_item(self, source_id, category, statement, confidence, origin, evidence):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO knowledge_source_items(source_id, category, statement, confidence, origin, evidence_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(source_id),
                (category or "knowledge").strip().lower(),
                (statement or "").strip(),
                float(confidence),
                (origin or "unknown").strip(),
                json.dumps(evidence or [], ensure_ascii=False),
                self._now(),
            )
        )
        self.conn.commit()

    def list_knowledge_source_items(self, category=None, created_at_prefix=None, limit=None):
        query = """
            SELECT k.id, k.source_id, s.name, k.category, k.statement, k.confidence, k.origin, k.evidence_json, k.created_at
            FROM knowledge_source_items k
            JOIN knowledge_sources s ON s.id = k.source_id
            WHERE 1=1
        """
        params = []
        if category:
            query += " AND k.category = ?"
            params.append(category)
        if created_at_prefix:
            query += " AND k.created_at LIKE ?"
            params.append(f"{created_at_prefix}%")
        query += " ORDER BY k.confidence DESC, k.created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(int(limit))
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def count_knowledge_sources(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM knowledge_sources")
        return cursor.fetchone()[0]

    def count_knowledge_source_items(self, category=None):
        query = "SELECT COUNT(*) FROM knowledge_source_items WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()[0]

    def most_important_knowledge_item(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT k.statement, k.category, k.confidence, s.name, k.created_at
            FROM knowledge_source_items k
            JOIN knowledge_sources s ON s.id = k.source_id
            ORDER BY k.confidence DESC, k.created_at DESC
            LIMIT 1
            """
        )
        return cursor.fetchone()

    def extract_concepts(self, text):
        words = [w.strip(".,!?;:") for w in text.split()]
        return [w.lower() for w in words if len(w) > 5][:3]


    # ==========================
    # REASONING V9
    # ==========================

    def save_reasoning_conclusion(self, category, statement, confidence, evidence, origin, created_at=None):
        evidence_json = json.dumps(evidence or [], ensure_ascii=False)
        self.conn.execute("""
            INSERT OR IGNORE INTO reasoning_conclusions(
                category, statement, confidence, evidence_json, origin, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (category, statement, float(confidence), evidence_json, origin, created_at or self._now()))
        self.conn.commit()

    def list_reasoning_conclusions(self, category=None):
        query = "SELECT id, category, statement, confidence, evidence_json, origin, created_at FROM reasoning_conclusions WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def count_reasoning_conclusions(self, category=None):
        query = "SELECT COUNT(*) FROM reasoning_conclusions WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()[0]


    # ==========================
    # AGENCY & ACTION V11
    # ==========================

    def save_intention(self, source_text, intention, confidence=0.0, status="observed"):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO intentions(source_text, intention_json, confidence, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_text or "", json.dumps(intention or {}, ensure_ascii=False), float(confidence or 0.0), status, self._now())
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_intentions(self, status=None, limit=None):
        query = "SELECT id, source_text, intention_json, confidence, status, created_at FROM intentions WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(int(limit))
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def save_agency_goal(self, intention_id, description, rationale="", priority=0.5, confidence=0.5, status="proposed"):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO agency_goals(intention_id, description, rationale, priority, confidence, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (intention_id, description or "", rationale or "", float(priority or 0.5), float(confidence or 0.5), status, self._now())
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_agency_goals(self, status=None, limit=None):
        query = "SELECT id, intention_id, description, rationale, priority, confidence, status, created_at FROM agency_goals WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(int(limit))
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def save_plan(self, goal_id, plan, status="proposed", requires_approval=True):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO plans(goal_id, plan_json, status, requires_approval, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (goal_id, json.dumps(plan or {}, ensure_ascii=False), status, 1 if requires_approval else 0, self._now())
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_plans(self, status=None, limit=None):
        query = "SELECT id, goal_id, plan_json, status, requires_approval, created_at FROM plans WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(int(limit))
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def upsert_tool(self, tool_id, capability, confidence=0.5, cost=0.0, latency=0.0, success_rate=0.5, enabled=True):
        now = self._now()
        self.conn.execute(
            """
            INSERT INTO tool_registry(id, capability, confidence, cost, latency, success_rate, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                capability = excluded.capability,
                confidence = excluded.confidence,
                cost = excluded.cost,
                latency = excluded.latency,
                success_rate = excluded.success_rate,
                enabled = excluded.enabled,
                updated_at = excluded.updated_at
            """,
            (tool_id, capability, float(confidence), float(cost), float(latency), float(success_rate), 1 if enabled else 0, now, now)
        )
        self.conn.commit()

    def list_tools(self, enabled_only=False):
        query = "SELECT id, capability, confidence, cost, latency, last_used, success_rate, enabled, created_at, updated_at FROM tool_registry"
        params = []
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY confidence DESC, success_rate DESC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def mark_tool_used(self, tool_id, success=True):
        now = self._now()
        cursor = self.conn.cursor()
        cursor.execute("SELECT success_rate FROM tool_registry WHERE id = ?", (tool_id,))
        row = cursor.fetchone()
        if not row:
            return
        previous = float(row[0])
        target = 1.0 if success else 0.0
        updated = (previous * 0.8) + (target * 0.2)
        self.conn.execute("UPDATE tool_registry SET last_used = ?, success_rate = ?, updated_at = ? WHERE id = ?", (now, updated, now, tool_id))
        self.conn.commit()

    def save_action(self, plan_id, tool_id, description, status="proposed", approval_required=True, result_summary=None, executed_at=None):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO actions(plan_id, tool_id, description, status, approval_required, result_summary, created_at, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (plan_id, tool_id, description or "", status, 1 if approval_required else 0, result_summary, self._now(), executed_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_action_status(self, action_id, status, result_summary=None, executed=False):
        executed_at = self._now() if executed else None
        self.conn.execute(
            """
            UPDATE actions
            SET status = ?, result_summary = COALESCE(?, result_summary), executed_at = COALESCE(?, executed_at)
            WHERE id = ?
            """,
            (status, result_summary, executed_at, int(action_id))
        )
        self.conn.commit()

    def list_actions(self, status=None, limit=None):
        query = "SELECT id, plan_id, tool_id, description, status, approval_required, result_summary, created_at, executed_at FROM actions WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(int(limit))
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def save_outcome(self, action_id, status, summary, reflection=""):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO outcomes(action_id, status, summary, reflection, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (action_id, status, summary or "", reflection or "", self._now())
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_outcomes(self, limit=None):
        query = "SELECT id, action_id, status, summary, reflection, created_at FROM outcomes ORDER BY created_at DESC"
        params = []
        if limit:
            query += " LIMIT ?"
            params.append(int(limit))
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
