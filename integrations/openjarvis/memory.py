"""Versioned personal facts, retrieval and contradiction history in SQLite."""
import json
import sqlite3
import time
import unicodedata


def key(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value)).casefold().split())


class PersonalMemory:
    def __init__(self, core):
        self.core = core
        self.tasks = core.local_tasks
        with self.tasks.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS personal_facts (
                id INTEGER PRIMARY KEY, subject TEXT NOT NULL, subject_key TEXT NOT NULL,
                fact TEXT NOT NULL, source TEXT NOT NULL, active INTEGER NOT NULL, created REAL NOT NULL)''')
            db.execute('CREATE INDEX IF NOT EXISTS personal_facts_subject ON personal_facts(subject_key,active)')
            columns={row[1] for row in db.execute('PRAGMA table_info(personal_facts)')}
            if 'attribute' not in columns:
                db.execute("ALTER TABLE personal_facts ADD COLUMN attribute TEXT NOT NULL DEFAULT ''")
            db.execute('CREATE TABLE IF NOT EXISTS agent_facts (subject TEXT PRIMARY KEY, fact TEXT NOT NULL, source TEXT NOT NULL, updated REAL NOT NULL)')
            # Idempotent migration of facts explicitly learned by the previous agent.
            db.execute('''INSERT INTO personal_facts(subject,subject_key,fact,source,active,created)
                SELECT subject,lower(trim(subject)),fact,source,1,updated FROM agent_facts a
                WHERE NOT EXISTS (SELECT 1 FROM personal_facts p WHERE p.subject_key=lower(trim(a.subject)))''')

        self.has_fts=False
        try:
            with self.tasks.connect() as db:
                db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS personal_facts_search USING fts5(subject,attribute,fact,tokenize='unicode61 remove_diacritics 2')")
                db.executescript("""
                    CREATE TRIGGER IF NOT EXISTS personal_fact_insert AFTER INSERT ON personal_facts WHEN NEW.active=1 BEGIN
                        INSERT INTO personal_facts_search(rowid,subject,attribute,fact) VALUES (NEW.id,NEW.subject,NEW.attribute,NEW.fact);
                    END;
                    CREATE TRIGGER IF NOT EXISTS personal_fact_update AFTER UPDATE ON personal_facts BEGIN
                        DELETE FROM personal_facts_search WHERE rowid=OLD.id;
                        INSERT INTO personal_facts_search(rowid,subject,attribute,fact) SELECT NEW.id,NEW.subject,NEW.attribute,NEW.fact WHERE NEW.active=1;
                    END;
                    CREATE TRIGGER IF NOT EXISTS personal_fact_delete AFTER DELETE ON personal_facts BEGIN
                        DELETE FROM personal_facts_search WHERE rowid=OLD.id;
                    END;
                """)
                db.execute('INSERT OR IGNORE INTO personal_facts_search(rowid,subject,attribute,fact) SELECT id,subject,attribute,fact FROM personal_facts WHERE active=1')
            self.has_fts=True
        except sqlite3.OperationalError:
            # SQLite builds without FTS5 retain bounded SQL retrieval.
            pass

    def remember(self, subject, fact, attribute='',source='explicit_user_request'):
        if not subject.strip() or len(subject) > 200 or not fact.strip() or len(fact) > 4000:
            raise ValueError('Assunto até 200 caracteres; informação até 4000')
        if not isinstance(attribute,str) or len(attribute)>200:
            raise ValueError('Atributo deve ser texto até 200 caracteres')
        if source not in {'explicit_user_request','conversation_statement'}:raise ValueError('Origem de memória inválida')
        normalized = key(subject)+('::'+key(attribute) if attribute else '')
        with self.tasks.connect() as db:
            previous = db.execute('SELECT id,fact FROM personal_facts WHERE subject_key=? AND active=1', (normalized,)).fetchone()
            if previous and previous[1] == fact:
                return {'saved': True, 'id': previous[0], 'subject': subject, 'fact': fact, 'unchanged': True}
            db.execute('UPDATE personal_facts SET active=0 WHERE subject_key=?', (normalized,))
            row = db.execute('INSERT INTO personal_facts(subject,subject_key,fact,source,active,created,attribute) VALUES (?,?,?,?,1,?,?)',
                             (subject, normalized, fact, source, time.time(),attribute))
            fact_id = row.lastrowid
        # Keep the established concepts/definitions API available to legacy modules.
        self.core.memory.save_definition(subject+(' / '+attribute if attribute else ''), fact)
        return {'saved': True, 'id': fact_id, 'subject': subject, 'fact': fact,
                'attribute':attribute,'superseded': previous[0] if previous else None, 'source': source}

    def search(self, query, limit=8):
        terms = key(query).split()[:16]
        with self.tasks.connect() as db:
            rows = db.execute('SELECT id,subject,fact,source,created,attribute FROM personal_facts WHERE active=1 ORDER BY created DESC LIMIT 100').fetchall()
            tokens=''.join(c if c.isalnum() else ' ' for c in key(query)).split()[:16]
            if self.has_fts and tokens:
                match=' OR '.join('"'+token+'"' for token in tokens)
                ids=[r[0] for r in db.execute('SELECT rowid FROM personal_facts_search WHERE personal_facts_search MATCH ? ORDER BY rank LIMIT 200',(match,))]
                if ids:
                    rows+=db.execute('SELECT id,subject,fact,source,created,attribute FROM personal_facts WHERE active=1 AND id IN ('+','.join('?' for _ in ids)+')',ids).fetchall()
            elif tokens:
                rows+=db.execute('SELECT id,subject,fact,source,created,attribute FROM personal_facts WHERE active=1 AND (lower(subject)=? OR fact LIKE ?) LIMIT 200',(key(query),'%'+tokens[0]+'%')).fetchall()
            rows=list({row[0]:row for row in rows}.values())
        def score(row):
            text = key(row[1]+' '+row[2]+' '+row[5])
            return (int(key(row[1]) == key(query))*20 + sum(term in text for term in terms))
        ranked = sorted(rows, key=lambda row:(score(row),row[4]), reverse=True)
        facts = [dict(zip(('id','subject','fact','source','created','attribute'),row)) for row in ranked if score(row)][:limit]
        # Existing definition / world-model data remain queryable, not silently deleted.
        legacy = []
        getter = getattr(self.core.memory, 'list_definitions', None)
        if getter:
            definitions = getter()
            for subject, meaning in definitions:
                if terms and any(term in key(subject+' '+meaning) for term in terms):
                    legacy.append({'subject': subject, 'fact': meaning, 'source': 'legacy_definition'})
                    if len(legacy) >= limit:
                        break
        layers=[];world=[]
        if hasattr(self.core.memory,'_now'):
            from memory.search import retrieve
            layers=retrieve(self.core.memory,query,limit=4)
            world=self.core.memory.conn.execute('''SELECT source,relation,target,confidence FROM world_relationships
                WHERE lower(source)=lower(?) OR lower(target)=lower(?) LIMIT 8''',(query,query)).fetchall()
        return {'facts': facts, 'legacy': legacy, 'memory_layers':layers,
                'world_relations':[dict(zip(('source','relation','target','confidence'),row)) for row in world],
                'participant': self.core.creator_name,'assistant': self.core.identity['name']}

    def history(self, subject):
        with self.tasks.connect() as db:
            rows = db.execute('SELECT id,fact,active,source,created,attribute FROM personal_facts WHERE lower(subject)=? OR subject_key=? ORDER BY created DESC LIMIT 20', (key(subject),key(subject))).fetchall()
        return {'subject': subject, 'versions': [dict(zip(('id','fact','active','source','created','attribute'),row)) for row in rows]}

    def context(self, query):
        result = self.search(query, 4)
        # Legacy lookup stays available through recall. Injecting common-word
        # matches from the whole knowledge base polluted every small turn.
        result.pop('legacy', None)
        result['memory_layers']=[item for item in result['memory_layers'] if item['confirmed']][:2]
        with self.tasks.connect() as db:
            recent = db.execute('SELECT subject,fact,source,attribute FROM personal_facts WHERE active=1 ORDER BY created DESC LIMIT 4').fetchall()
        result['recent'] = [dict(zip(('subject','fact','source','attribute'),row)) for row in recent]
        return json.dumps(result, ensure_ascii=False)[:5000]
