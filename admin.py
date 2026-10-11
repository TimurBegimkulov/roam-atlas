"""Owner-only administration. Secrets are configured through hosting environment variables."""
import hashlib
import hmac
import json
import os
import secrets
import time
from http.cookies import SimpleCookie

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
    return f'pbkdf2-sha256$600000${salt}${digest}'

def verify(password, encoded):
    try:
        scheme,iterations,salt,digest=encoded.split('$')
        if scheme!='pbkdf2-sha256' or iterations!='600000': return False
        return hmac.compare_digest(password_hash(password,salt),encoded)
    except (ValueError,TypeError): return False

def handle(env,headers,reply,connect):
    path,method=env['PATH_INFO'],env['REQUEST_METHOD']
    configured=os.environ.get('ADMIN_PASSWORD_HASH','')
    if not configured: return reply({'error':'Administration is not configured'},'503 Service Unavailable')
    secure=bool(os.environ.get('SITE_URL')) or env.get('HTTP_X_FORWARDED_PROTO',env.get('wsgi.url_scheme'))=='https'
    cookie_flags='; Path=/api/admin; HttpOnly; SameSite=Strict'+('; Secure' if secure else '')
    if method in ('POST','DELETE'):
        origin=env.get('HTTP_ORIGIN','')
        if env.get('HTTP_X_ORBIT_REQUEST')!='1' or (origin and origin.split('://')[-1]!=env.get('HTTP_HOST')):
            return reply({'error':'Forbidden'},'403 Forbidden')
    now=int(time.time())
    fingerprint=hashlib.sha256(configured.encode()).hexdigest()
    with connect() as con:
        con.executescript('''CREATE TABLE IF NOT EXISTS admin_sessions (token TEXT PRIMARY KEY, expires INTEGER NOT NULL, fingerprint TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS admin_attempts (address TEXT PRIMARY KEY, attempts INTEGER NOT NULL, reset INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS admin_audit (at INTEGER NOT NULL, action TEXT NOT NULL, target TEXT);''')
        con.execute('DELETE FROM admin_sessions WHERE expires<=? OR fingerprint!=?',(now,fingerprint))
        con.execute('DELETE FROM admin_attempts WHERE reset<=?',(now,))
        con.execute('DELETE FROM admin_audit WHERE at<?',(now-90*86400,))
        if path=='/api/admin/login' and method=='POST':
            # Do not trust client-supplied X-Forwarded-For. At a reverse proxy this can
            # conservatively rate-limit all visitors behind the proxy together.
            address=hashlib.sha256(env.get('REMOTE_ADDR','unknown').encode()).hexdigest()
            attempts=con.execute('SELECT attempts FROM admin_attempts WHERE address=?',(address,)).fetchone()
            if attempts and attempts[0]>=5:
                headers.append(('Retry-After','900'))
                return reply({'error':'Too many attempts. Try again in 15 minutes.'},'429 Too Many Requests')
            con.execute('INSERT INTO admin_attempts VALUES (?,1,?) ON CONFLICT(address) DO UPDATE SET attempts=attempts+1',(address,now+900))
            try:
                length=int(env.get('CONTENT_LENGTH') or 0)
                if not 0<length<=2048: raise ValueError()
                data=json.loads(env['wsgi.input'].read(length))
                username,password=data['username'],data['password']
                if not isinstance(username,str) or not isinstance(password,str) or len(password)>256: raise ValueError()
            except (ValueError,TypeError,KeyError): return reply({'error':'Invalid credentials'},'401 Unauthorized')
            valid_password=verify(password,configured)
            if not valid_password or not hmac.compare_digest(username.encode(),os.environ.get('ADMIN_USERNAME','admin').encode()):
                con.execute('INSERT INTO admin_audit VALUES (?,?,?)',(now,'login_failed',None))
                return reply({'error':'Invalid credentials'},'401 Unauthorized')
            con.execute('DELETE FROM admin_attempts WHERE address=?',(address,))
            token=secrets.token_urlsafe(48)
            # New login revokes any previous admin session.
            con.execute('DELETE FROM admin_sessions')
            con.execute('INSERT INTO admin_sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),now+3600,fingerprint))
            con.execute('INSERT INTO admin_audit VALUES (?,?,?)',(now,'login',None))
            headers.append(('Set-Cookie',f'roam_admin={token}; Max-Age=3600{cookie_flags}'))
            return reply({'ok':True,'expiresIn':3600})
        cookies=SimpleCookie()
        try: cookies.load(env.get('HTTP_COOKIE',''))
        except Exception: pass
        token=cookies['roam_admin'].value if 'roam_admin' in cookies else ''
        token_hash=hashlib.sha256(token.encode()).hexdigest()
        if not con.execute('SELECT 1 FROM admin_sessions WHERE token=? AND expires>? AND fingerprint=?',(token_hash,now,fingerprint)).fetchone():
            return reply({'error':'Sign in required'},'401 Unauthorized')
        if path=='/api/admin/logout' and method=='POST':
            con.execute('DELETE FROM admin_sessions WHERE token=?',(token_hash,))
            headers.append(('Set-Cookie',f'roam_admin=; Max-Age=0{cookie_flags}'))
            return reply({'ok':True})
        if path=='/api/admin/overview' and method=='GET':
            trips=[json.loads(r['data']) for r in con.execute('SELECT data FROM trips ORDER BY rowid DESC LIMIT 500')]
            return reply({'trips':trips,'tripCount':con.execute('SELECT COUNT(*) FROM trips').fetchone()[0],'visitorCount':con.execute('SELECT COUNT(*) FROM visitors').fetchone()[0],'audit':[dict(r) for r in con.execute('SELECT at,action,target FROM admin_audit ORDER BY rowid DESC LIMIT 30')]})
        if path.startswith('/api/admin/trips/') and method=='DELETE':
            trip_id=path.rsplit('/',1)[1]
            changed=con.execute('DELETE FROM trips WHERE id=?',(trip_id,)).rowcount
            if changed: con.execute('INSERT INTO admin_audit VALUES (?,?,?)',(now,'delete_trip',trip_id))
            return reply({'deleted':bool(changed)},'200 OK' if changed else '404 Not Found')
        return reply({'error':'Not found'},'404 Not Found')
