"""Optional SQLite FTS5 index; candidates and confirmed memory stay distinct."""
import sqlite3


def initialize(memory):
    try:
        memory.conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(layer UNINDEXED, source_id UNINDEXED, content, tokenize='unicode61 remove_diacritics 2')")
        memory.conn.execute('CREATE TABLE IF NOT EXISTS memory_migrations(name TEXT PRIMARY KEY)')
        for layer,table,column in [('short','short_term_memory','content'),('mid','mid_term_memory','summary'),('long','long_term_memory','content')]:
            memory.conn.execute(f'''CREATE TRIGGER IF NOT EXISTS fts_{layer}_insert AFTER INSERT ON {table} BEGIN
                INSERT INTO memory_fts(layer,source_id,content) VALUES ('{layer}',new.id,new.{column}); END''')
            memory.conn.execute(f'''CREATE TRIGGER IF NOT EXISTS fts_{layer}_update AFTER UPDATE ON {table} BEGIN
                DELETE FROM memory_fts WHERE layer='{layer}' AND source_id=old.id;
                INSERT INTO memory_fts(layer,source_id,content) VALUES ('{layer}',new.id,new.{column}); END''')
            memory.conn.execute(f'''CREATE TRIGGER IF NOT EXISTS fts_{layer}_delete AFTER DELETE ON {table} BEGIN
                DELETE FROM memory_fts WHERE layer='{layer}' AND source_id=old.id; END''')
        if not memory.conn.execute("SELECT 1 FROM memory_migrations WHERE name='fts_v1'").fetchone():
            memory.conn.execute('DELETE FROM memory_fts')
            for layer,table,column in [('short','short_term_memory','content'),('mid','mid_term_memory','summary'),('long','long_term_memory','content')]:
                memory.conn.execute(f"INSERT INTO memory_fts(layer,source_id,content) SELECT ?,id,{column} FROM {table}",(layer,))
            memory.conn.execute("INSERT INTO memory_migrations(name) VALUES ('fts_v1')")
        return True
    except sqlite3.OperationalError:
        return False


def retrieve(memory, query, limit=10):
    normalized=''.join(c if c.isalnum() else ' ' for c in str(query)).split()[:12]
    if not normalized: return []
    match=' OR '.join('"'+term+'"' for term in normalized)
    now=memory._now()
    try:
        rows=memory.conn.execute('''SELECT layer,source_id,content,bm25(memory_fts) FROM memory_fts
            WHERE memory_fts MATCH ? AND (
            (layer='short' AND source_id IN (SELECT id FROM short_term_memory WHERE archived=0 AND expires_at>?)) OR
            (layer='mid' AND source_id IN (SELECT id FROM mid_term_memory WHERE archived=0 AND expires_at>?)) OR layer='long')
            ORDER BY bm25(memory_fts) LIMIT ?''',(match,now,now,max(1,min(int(limit),30)))).fetchall()
    except sqlite3.OperationalError:
        # Builds without FTS5 keep a bounded lexical fallback.
        rows=[]
        for layer,items in [('long',memory.list_long_term_memory()),('mid',memory.list_mid_term_memory()),('short',memory.list_short_term_memory())]:
            for item in items:
                score=sum(term.casefold() in item[1].casefold() for term in normalized)
                if score: rows.append((layer,item[0],item[1],-score))
        rows.sort(key=lambda row:row[3]); rows=rows[:limit]
    return [dict(layer=layer,id=source_id,content=content,rank=rank,confirmed=layer=='long') for layer,source_id,content,rank in rows]
