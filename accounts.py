"""Password-based user accounts and revocable, hashed server-side sessions."""
import hashlib
import json
import re
import secrets
import time
from http.cookies import SimpleCookie
import admin

def schema(con):
    con.executescript('''CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS user_sessions (token TEXT PRIMARY KEY, owner TEXT NOT NULL, expires BIGINT NOT NULL);
    CREATE TABLE IF NOT EXISTS user_attempts (address TEXT PRIMARY KEY, attempts INTEGER NOT NULL, reset BIGINT NOT NULL);''')

def token(env):
    cookies=SimpleCookie()
    try: cookies.load(env.get('HTTP_COOKIE',''))
    except Exception: pass
    return hashlib.sha256(cookies['roam_user'].value.encode()).hexdigest() if 'roam_user' in cookies else ''

def current(con,env):
    schema(con)
    return con.execute('SELECT users.id, users.username FROM users JOIN user_sessions ON users.id=user_sessions.owner WHERE user_sessions.token=? AND user_sessions.expires>?',(token(env),int(time.time()))).fetchone()

def handle(env,headers,reply,connect):
    path,method=env['PATH_INFO'],env['REQUEST_METHOD']
    now=int(time.time())
    flags='; Path=/; HttpOnly; SameSite=Strict'+('; Secure' if env.get('HTTP_X_FORWARDED_PROTO',env.get('wsgi.url_scheme'))=='https' else '')
    if method!='GET':
        origin=env.get('HTTP_ORIGIN','')
        if env.get('HTTP_X_ORBIT_REQUEST')!='1' or (origin and origin.split('://')[-1]!=env.get('HTTP_HOST')):
            return reply({'error':'Forbidden'},'403 Forbidden')
    with connect() as con:
        user=current(con,env)
        con.execute('DELETE FROM user_sessions WHERE expires<=?',(now,))
        con.execute('DELETE FROM user_attempts WHERE reset<=?',(now,))
        if path=='/api/account' and method=='GET':
            return reply({'user':{'username':user['username']} if user else None})
        if path=='/api/account/logout' and method=='POST':
            con.execute('DELETE FROM user_sessions WHERE token=?',(token(env),))
            headers.append(('Set-Cookie','roam_user=; Max-Age=0'+flags))
            return reply({'ok':True})
        if path not in ('/api/account/register','/api/account/login') or method!='POST':
            return reply({'error':'Not found'},'404 Not Found')
        address=hashlib.sha256(env.get('REMOTE_ADDR','unknown').encode()).hexdigest()
        attempts=con.execute('SELECT attempts FROM user_attempts WHERE address=?',(address,)).fetchone()
        if attempts and attempts[0]>=10:
            headers.append(('Retry-After','900'))
            return reply({'error':'rate_limit'},'429 Too Many Requests')
        con.execute('INSERT INTO user_attempts VALUES (?,1,?) ON CONFLICT(address) DO UPDATE SET attempts=user_attempts.attempts+1',(address,now+900))
        try:
            length=int(env.get('CONTENT_LENGTH') or 0)
            if not 0<length<=2048: raise ValueError()
            data=json.loads(env['wsgi.input'].read(length))
            username=data['username'].strip().lower()
            password=data['password']
            if not re.fullmatch(r'[a-z0-9_.-]{3,32}',username) or not isinstance(password,str) or not 12<=len(password)<=128: raise ValueError()
        except (ValueError,TypeError,KeyError,AttributeError):
            return reply({'error':'invalid_fields'},'400 Bad Request')
        existing=con.execute('SELECT id,password FROM users WHERE username=?',(username,)).fetchone()
        if path.endswith('/register'):
            if existing: return reply({'error':'username_unavailable'},'409 Conflict')
            owner='user:'+secrets.token_hex(16)
            con.execute('INSERT INTO users (id,username,password) VALUES (?,?,?)',(owner,username,admin.password_hash(password)))
            # Claim guest trips only when creating a new account in the same browser.
            cookies=SimpleCookie()
            try: cookies.load(env.get('HTTP_COOKIE',''))
            except Exception: pass
            if 'orbit_session' in cookies:
                guest=hashlib.sha256(cookies['orbit_session'].value.encode()).hexdigest()
                con.execute('UPDATE trips SET owner=? WHERE owner=?',(owner,guest))
        else:
            encoded=existing['password'] if existing else admin.password_hash('dummy-account-password')
            valid=admin.verify(password,encoded)
            if not existing or not valid: return reply({'error':'invalid_credentials'},'401 Unauthorized')
            owner=existing['id']
        con.execute('DELETE FROM user_attempts WHERE address=?',(address,))
        con.execute('DELETE FROM user_sessions WHERE token=?',(token(env),))
        session=secrets.token_urlsafe(48)
        con.execute('INSERT INTO user_sessions VALUES (?,?,?)',(hashlib.sha256(session.encode()).hexdigest(),owner,now+30*86400))
        headers.append(('Set-Cookie',f'roam_user={session}; Max-Age={30*86400}'+flags))
        return reply({'user':{'username':username}})
