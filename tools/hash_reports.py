"""Explicit private hash-feedback inbox. No original text, network or training labels."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote
import re
import sqlite3
import stat
import sys
import time
import uuid
from tools.blind_review_io import directory,member,create,source
ROOT=Path(__file__).resolve().parents[1]
FORMAT='local-hash-feedback/v1'
CODES=('PS','PII_REDACTED')
CATEGORIES=('false_alarm','missed_pattern','unavailable','unclear')
MAX_RECORDS=10000
MAX_DB=16*1024*1024
SENSITIVE={'.git','.ssh','.gnupg','.aws','.config','library','.password-store'}
TABLES={
 'settings':"CREATE TABLE settings(singleton INTEGER PRIMARY KEY CHECK(singleton=1),format TEXT NOT NULL,days INTEGER NOT NULL CHECK(days BETWEEN 1 AND 30)) STRICT",
 'reports':"CREATE TABLE reports(ticket TEXT PRIMARY KEY,subject TEXT NOT NULL,method TEXT NOT NULL,code TEXT NOT NULL,category TEXT NOT NULL,created INTEGER NOT NULL,expires INTEGER NOT NULL,UNIQUE(subject,method,code,category)) STRICT"}
class Refused(ValueError):pass
def require(ok):
    if not ok:raise Refused('Hash report inbox unavailable')
def encode(d):return json.dumps(d,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def unique(pairs):
    d={}
    for k,v in pairs:require(k not in d);d[k]=v
    return d

def parse(raw,limit=4096):
    require(type(raw) is bytes and 0<len(raw)<=limit)
    d=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(Refused('Hash report inbox unavailable')))
    require(type(d) is dict);return d

def hash_value(v):require(type(v) is str and re.fullmatch('[a-f0-9]{64}',v));return v
def ticket(v):require(type(v) is str and str(uuid.UUID(v))==v and uuid.UUID(v).version==4);return v

def feedback(d):
    require(set(d)=={'format','subject_sha256','method_sha256','code','category'})
    require(d['format']==FORMAT and d['code'] in CODES and d['category'] in CATEGORIES)
    hash_value(d['subject_sha256']);hash_value(d['method_sha256']);return d

def scope(path):
    require(sys.platform in ('darwin','linux') and os.geteuid()!=0)
    p=Path(path).expanduser().absolute();r=p.resolve(strict=True)
    require(not any(q.is_symlink() for q in (p,*p.parents)))
    require(not any(x.lower() in SENSITIVE for x in r.parts))
    require(not any((q/'.git').exists() for q in (r,*r.parents)))
    with directory(p,ROOT):pass
    return p

def publish(path,raw):
    p=Path(path).expanduser().absolute();scope(p.parent)
    with directory(p.parent,ROOT) as fd:
        out=os.open(p.name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=fd)
        try:
            with os.fdopen(out,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.fsync(fd)
        except BaseException:
            # Preserve an interrupted export for explicit operator review.
            raise

def connection(path):
    db=sqlite3.connect('file:'+quote(str(path),safe='/')+'?mode=rw',uri=True,timeout=5)
    try:
        db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA temp_store=MEMORY');db.execute('PRAGMA secure_delete=ON');db.execute('PRAGMA max_page_count=4096')
        require(db.execute('PRAGMA journal_mode=DELETE').fetchone()[0]=='delete')
        return db
    except BaseException:db.close();raise

class Inbox:
    def __init__(self,path):self.path=Path(path).expanduser().absolute()
    @staticmethod
    def initialize(path,days=30):
        require(type(days) is int and 1<=days<=30);path=Path(path).expanduser().absolute();scope(path.parent)
        require(path.name.lower() not in SENSITIVE)
        # Build the empty database before publishing the new owned directory.
        db=sqlite3.connect(':memory:')
        try:
            db.execute('PRAGMA auto_vacuum=FULL')
            for statement in TABLES.values():db.execute(statement)
            db.execute('INSERT INTO settings VALUES(1,?,?)',('local-hash-inbox/v1',days));db.commit();raw=db.serialize()
        finally:db.close()
        create(path,ROOT,{'reports.sqlite':raw,'access.lock':b''})
        return {'initialized':True,'days':days,'company_collection_enabled':False,'public_registry_enabled':False,'automatic_upload':False}
    @contextmanager
    def transaction(self):
        scope(self.path)
        with directory(self.path,ROOT) as fd:
            lock=os.open('access.lock',os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
            db=None
            try:
                info=os.fstat(lock);require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_nlink==1 and not info.st_mode&0o077 and info.st_size==0)
                fcntl.flock(lock,fcntl.LOCK_EX)
                current=self.path.stat(follow_symlinks=False);held=os.fstat(fd);require((current.st_dev,current.st_ino)==(held.st_dev,held.st_ino))
                require(set(os.listdir(fd))<={'reports.sqlite','reports.sqlite-journal','access.lock'} and {'reports.sqlite','access.lock'}<=set(os.listdir(fd)))
                # No-follow private-member validation precedes SQLite's own file opening.
                for name in os.listdir(fd):member(fd,name,MAX_DB)
                db=connection(self.path/'reports.sqlite');db.execute('BEGIN IMMEDIATE')
                schema={name:sql for kind,name,sql in db.execute("SELECT type,name,sql FROM sqlite_schema WHERE name NOT GLOB 'sqlite_*'") if kind=='table'}
                other=db.execute("SELECT count(*) FROM sqlite_schema WHERE name NOT GLOB 'sqlite_*' AND type!='table'").fetchone()[0]
                require(schema==TABLES and other==0)
                settings=db.execute('SELECT singleton,format,days FROM settings').fetchall();require(len(settings)==1)
                one,fmt,days=settings[0];require(one==1 and fmt=='local-hash-inbox/v1' and type(days) is int and 1<=days<=30)
                yield db,days
                current=self.path.stat(follow_symlinks=False);require((current.st_dev,current.st_ino)==(held.st_dev,held.st_ino))
                db.commit()
            except BaseException:
                if db is not None:db.rollback()
                raise
            finally:
                if db is not None:db.close()
                os.close(lock)
    @staticmethod
    def prune_rows(db):
        now=int(time.time());require(now>0)
        return db.execute('DELETE FROM reports WHERE expires<=?',(now,)).rowcount
    def ingest(self,d,*,consent=False):
        require(consent is True);d=feedback(d)
        with self.transaction() as (db,days):
            self.prune_rows(db);now=int(time.time());require(now>0)
            selected=(d['subject_sha256'],d['method_sha256'],d['code'],d['category'])
            existing=db.execute('SELECT ticket,created,expires FROM reports WHERE subject=? AND method=? AND code=? AND category=?',selected).fetchone()
            if existing:
                identifier,created,expires=existing;ticket(identifier);require(type(created) is int and type(expires) is int and expires==created+days*86400)
                return {'ticket':identifier,'duplicate':True,'created_at':created,'expires_at':expires,'verified':False,'training_label':None}
            require(db.execute('SELECT count(*) FROM reports').fetchone()[0]<MAX_RECORDS)
            identifier=str(uuid.uuid4());expires=now+days*86400
            db.execute('INSERT INTO reports VALUES(?,?,?,?,?,?,?)',(identifier,*selected,now,expires))
            return {'ticket':identifier,'duplicate':False,'created_at':now,'expires_at':expires,'verified':False,'training_label':None}
    def stats(self):
        with self.transaction() as (db,days):
            removed=self.prune_rows(db);counts=[{'code':a,'category':b,'count':n} for a,b,n in db.execute('SELECT code,category,count(*) FROM reports GROUP BY code,category ORDER BY code,category')]
            require(all(x['code'] in CODES and x['category'] in CATEGORIES and type(x['count']) is int and x['count']>0 for x in counts))
            return {'format':'local-hash-inbox-status/v1','active_records':sum(x['count'] for x in counts),'expired_removed':removed,'retention_days':days,'counts':counts,'company_collection_enabled':False,'public_registry_enabled':False,'automatic_upload':False,'all_feedback_unverified':True}
    def export(self):
        with self.transaction() as (db,days):
            self.prune_rows(db);rows=[]
            for identifier,subject,method,code,category,created,expires in db.execute('SELECT ticket,subject,method,code,category,created,expires FROM reports ORDER BY created,ticket LIMIT 10001'):
                ticket(identifier);d=feedback({'format':FORMAT,'subject_sha256':subject,'method_sha256':method,'code':code,'category':category})
                require(type(created) is int and type(expires) is int and 0<created<=time.time()+5 and expires==created+days*86400 and expires>time.time())
                rows.append({'ticket':identifier,'feedback':d,'created_at':created,'expires_at':expires,'verified':False,'training_label':None})
            require(len(rows)<=MAX_RECORDS)
            return {'format':'local-hash-feedback-export/v1','retention_days':days,'records':rows,'verified':False,'training_labels_included':False,'company_collection_enabled':False,'public_registry_enabled':False}
    def withdraw(self,identifier):
        ticket(identifier)
        with self.transaction() as (db,days):
            self.prune_rows(db);n=db.execute('DELETE FROM reports WHERE ticket=?',(identifier,)).rowcount
            return {'withdrawn':n==1,'logical_deletion':True,'external_copies_removed':False}
    def remove(self,*,consent=False):
        require(consent is True)
        # transaction() verifies the whole owned namespace. No recursive removal.
        with self.transaction() as (db,days):pass
        # Reacquire the same lock and revalidate all members before removing them.
        scope(self.path)
        with directory(self.path,ROOT) as fd:
            lock=os.open('access.lock',os.O_RDWR|os.O_NOFOLLOW,dir_fd=fd)
            try:
                fcntl.flock(lock,fcntl.LOCK_EX);require(set(os.listdir(fd))=={'reports.sqlite','access.lock'})
                for name in os.listdir(fd):member(fd,name,MAX_DB)
                current=self.path.stat(follow_symlinks=False);held=os.fstat(fd);require((current.st_dev,current.st_ino)==(held.st_dev,held.st_ino))
                os.unlink('reports.sqlite',dir_fd=fd);os.unlink('access.lock',dir_fd=fd);os.fsync(fd);self.path.rmdir()
            finally:os.close(lock)
        return {'removed':True,'external_copies_removed':False,'personal_checker_changed':False}
