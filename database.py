"""PostgreSQL adapter for durable storage on free hosting.

Local development continues to use SQLite. PostgreSQL credentials come only
from DATABASE_URL in the host environment; they are never sent to browsers.
"""
import re

class Row(dict):
    def __getitem__(self,key):
        return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)

class Cursor:
    def __init__(self,cursor): self.cursor=cursor
    @property
    def rowcount(self): return self.cursor.rowcount
    def fetchone(self):
        value=self.cursor.fetchone()
        return Row(value) if value is not None else None
    def __iter__(self):
        return (Row(value) for value in self.cursor)

class Connection:
    def __init__(self,url):
        import psycopg
        from psycopg.rows import dict_row
        self.raw=psycopg.connect(url,connect_timeout=15,row_factory=dict_row,sslmode='require')
    def execute(self,sql,parameters=()):
        return Cursor(self.raw.execute(sql.replace('?','%s'),parameters))
    def executescript(self,script):
        # Schema changes are serialized across workers, including first boot.
        self.raw.execute('SELECT pg_advisory_xact_lock(72019301)')
        script=re.sub(r'trips\s*\(id', 'trips (rowid BIGSERIAL UNIQUE, id',script)
        script=re.sub(r'admin_audit\s*\(at', 'admin_audit (rowid BIGSERIAL UNIQUE, at',script)
        for statement in script.split(';'):
            if statement.strip(): self.raw.execute(statement)
    def __enter__(self): return self
    def __exit__(self,kind,value,traceback):
        if kind: self.raw.rollback()
        else: self.raw.commit()
    def close(self): self.raw.close()
