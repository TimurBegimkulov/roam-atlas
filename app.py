"""Orbit: dependency-free WSGI app; Gunicorn serves the same app in production."""
import datetime as dt
from contextlib import contextmanager
import hashlib
import admin
import accounts
import catalog
from html import escape
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import urlsplit
from http.cookies import SimpleCookie
from wsgiref.simple_server import make_server

ROOT = Path(__file__).parent
DB = os.environ.get('DATABASE_PATH', str(ROOT / 'data' / 'orbit.sqlite3'))

def public_url():
    value = os.environ.get('SITE_URL', '').strip().rstrip('/')
    parsed = urlsplit(value)
    if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password and parsed.path in ('', '/') and not parsed.query and not parsed.fragment:
        return value
    return ''

def search_metadata():
    origin = public_url()
    metadata = '<meta property="og:type" content="website"><meta property="og:site_name" content="Roam Atlas"><meta property="og:title" content="Roam Atlas — Travel Planner"><meta property="og:description" content="Plan your next adventure with itineraries, travel budgets and packing checklists. Available in English and Russian."><meta name="twitter:card" content="summary_large_image"><meta property="og:image" content="https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&amp;fit=crop&amp;w=1200&amp;q=85">'
    if origin:
        metadata += f'<link rel="canonical" href="{escape(origin)}/"><meta property="og:url" content="{escape(origin)}/"><meta name="robots" content="index,follow,max-image-preview:large">'
    else:
        metadata += '<meta name="robots" content="noindex,nofollow">'
    verification = os.environ.get('GOOGLE_SITE_VERIFICATION', '').strip()
    if verification:
        metadata += f'<meta name="google-site-verification" content="{escape(verification)}">'
    return metadata
DESTINATIONS = [
    dict(id='dolomites', name='The Dolomites', ru='Доломиты', country='Italy', country_ru='Италия', category='mountains', days=5, cost=850, image='photo-1464822759023-fed622ff2c3b', tag='Above the ordinary', tag_ru='Выше обыденности'),
    dict(id='kyoto', name='Kyoto', ru='Киото', country='Japan', country_ru='Япония', category='culture', days=7, cost=1400, image='photo-1493976040374-85c8e12f0c0e', tag='Take the scenic route', tag_ru='Дорога к прекрасному'),
    dict(id='bali', name='Bali', ru='Бали', country='Indonesia', country_ru='Индонезия', category='coast', days=8, cost=950, image='photo-1537996194471-e657df975ab4', tag='Find your own rhythm', tag_ru='Найдите свой ритм'),
    dict(id='iceland', name='South Iceland', ru='Южная Исландия', country='Iceland', country_ru='Исландия', category='mountains', days=6, cost=1650, image='photo-1476610182048-b716b8518aae', tag='A little more wild', tag_ru='Навстречу природе'),
    dict(id='porto', name='Porto', ru='Порту', country='Portugal', country_ru='Португалия', category='culture', days=4, cost=650, image='photo-1555881400-74d7acaacd8b', tag='Slow mornings, golden evenings', tag_ru='Тихое утро, золотой вечер'),
    dict(id='santorini', name='Santorini', ru='Санторини', country='Greece', country_ru='Греция', category='coast', days=5, cost=1100, image='photo-1533105079780-92b9be482077', tag='Somewhere by the sea', tag_ru='Где-то у моря'),
]

@contextmanager
def connect():
    database_url=os.environ.get('DATABASE_URL','').strip()
    if database_url:
        from database import Connection
        con=Connection(database_url)
    else:
        if os.environ.get('RENDER')=='true':
            raise RuntimeError('DATABASE_URL must be configured for durable free hosting')
        Path(DB).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(DB, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA journal_mode=WAL')
    try:
        with con:
            con.executescript('''CREATE TABLE IF NOT EXISTS visitors (id TEXT PRIMARY KEY);
              CREATE TABLE IF NOT EXISTS trips (id TEXT PRIMARY KEY, owner TEXT NOT NULL, data TEXT NOT NULL);''')
            yield con
    finally:
        con.close()

def application(env, start_response):
    status = '200 OK'
    headers = [('X-Content-Type-Options','nosniff'), ('Referrer-Policy','strict-origin-when-cross-origin'),
               ('X-Frame-Options','DENY'), ('Content-Security-Policy', "default-src 'self'; img-src 'self' https://images.unsplash.com https://upload.wikimedia.org https://thumb.wikimedia.org; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")]
    path, method = env.get('PATH_INFO','/'), env['REQUEST_METHOD']
    if public_url():
        headers.append(('Strict-Transport-Security','max-age=31536000'))
    if path.startswith('/api/'):
        headers.append(('X-Robots-Tag','noindex, nofollow'))
    def reply(data, code='200 OK'):
        raw = json.dumps(data, ensure_ascii=False).encode()
        start_response(code, headers + [('Content-Type','application/json; charset=utf-8'), ('Cache-Control','no-store'), ('Content-Length',str(len(raw)))])
        return [raw]
    if path.startswith('/api/account'):
        return accounts.handle(env,headers,reply,connect)
    if path == '/api/world' and method == 'GET':
        return reply(catalog.search(env.get('QUERY_STRING','')))
    if path == '/api/countries' and method == 'GET':
        return reply(catalog.COUNTRIES)
    if path.startswith('/api/admin/'):
        return admin.handle(env,headers,reply,connect)
    if path == '/api/health':
        return reply({'status':'ok','service':'orbit'})
    if path == '/api/destinations' and method == 'GET':
        return reply(DESTINATIONS)
    if path in ('/robots.txt', '/sitemap.xml') and method in ('GET','HEAD'):
        origin = public_url()
        if path == '/robots.txt':
            content = (f'User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {origin}/sitemap.xml\n' if origin else 'User-agent: *\nDisallow: /\n').encode()
            mime = 'text/plain'
        else:
            if not origin: return reply({'error':'Public origin is not configured'},'503 Service Unavailable')
            content = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{escape(origin)}/</loc></url></urlset>'.encode()
            mime = 'application/xml'
        start_response('200 OK', headers + [('Content-Type',mime+'; charset=utf-8'),('Content-Length',str(len(content)))])
        return [content] if method == 'GET' else []
    if path.startswith('/api/'):
        cookie = SimpleCookie()
        try: cookie.load(env.get('HTTP_COOKIE',''))
        except Exception: pass
        token = cookie['orbit_session'].value if 'orbit_session' in cookie else ''
        owner = hashlib.sha256(token.encode()).hexdigest()
        with connect() as con:
            user=accounts.current(con,env)
            if user: owner=user['id']
            if not user and not con.execute('SELECT 1 FROM visitors WHERE id=?',(owner,)).fetchone():
                token = secrets.token_urlsafe(32)
                owner = hashlib.sha256(token.encode()).hexdigest()
                con.execute('INSERT INTO visitors VALUES (?)',(owner,))
                secure = '; Secure' if env.get('HTTP_X_FORWARDED_PROTO',env.get('wsgi.url_scheme')) == 'https' else ''
                headers.append(('Set-Cookie',f'orbit_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000{secure}'))
            if method in ('POST','PUT','DELETE'):
                origin = env.get('HTTP_ORIGIN','')
                if env.get('HTTP_X_ORBIT_REQUEST') != '1' or (origin and origin.split('://')[-1] != env.get('HTTP_HOST')):
                    return reply({'error':'Forbidden'},'403 Forbidden')
            if path == '/api/trips' and method == 'GET':
                records=[json.loads(r['data']) for r in con.execute('SELECT data FROM trips WHERE owner=? ORDER BY rowid DESC',(owner,))]
                for record in records:
                    if record['destination'] in catalog.BY_ID: record['destinationInfo']=catalog.destination(catalog.BY_ID[record['destination']])
                return reply(records)
            if path == '/api/trips' and method == 'POST':
                if con.execute('SELECT COUNT(*) FROM trips WHERE owner=?',(owner,)).fetchone()[0] >= 100:
                    return reply({'error':'Trip limit reached'},'400 Bad Request')
            if (path == '/api/trips' and method == 'POST') or (path.startswith('/api/trips/') and method == 'PUT'):
                try:
                    length = int(env.get('CONTENT_LENGTH') or 0)
                    if not 0 < length <= 20000: raise ValueError()
                    data = json.loads(env['wsgi.input'].read(length))
                    if not isinstance(data,dict): raise ValueError()
                    title = data['title'].strip()
                    if not 1 <= len(title) <= 100: raise ValueError()
                    if data['destination'] not in {d['id'] for d in DESTINATIONS} and data['destination'] not in catalog.BY_ID: raise ValueError()
                    if isinstance(data['days'], bool) or isinstance(data['budget'], bool): raise ValueError()
                    days, budget = int(data['days']), float(data['budget'])
                    if isinstance(data['days'], float) and data['days'] != days: raise ValueError()
                    if not 1 <= days <= 60 or not math.isfinite(budget) or not 0 <= budget <= 1000000: raise ValueError()
                    date = data.get('date','')
                    if date: dt.date.fromisoformat(date)
                    notes = data.get('notes','')
                    if not isinstance(notes,str) or len(notes)>3000: raise ValueError()
                    packed = data.get('packed',[])
                    if not isinstance(packed,list) or any(type(x) is not int or x not in range(6) for x in packed): raise ValueError()
                    itinerary = data.get('itinerary',[])
                    if not isinstance(itinerary,list) or len(itinerary)>60 or any(not isinstance(x,str) or len(x)>200 for x in itinerary): raise ValueError()
                    trip_id = secrets.token_hex(12) if method == 'POST' else path.rsplit('/',1)[1]
                    record = dict(id=trip_id,title=title,destination=data['destination'],days=days,budget=budget,date=date,notes=notes,packed=sorted(set(packed)),itinerary=itinerary)
                except (ValueError,KeyError,TypeError,AttributeError,OverflowError):
                    return reply({'error':'Invalid trip data'},'400 Bad Request')
                if method == 'PUT' and not con.execute('SELECT 1 FROM trips WHERE id=? AND owner=?',(trip_id,owner)).fetchone():
                    return reply({'error':'Not found'},'404 Not Found')
                if method == 'POST': con.execute('INSERT INTO trips (id,owner,data) VALUES (?,?,?)',(trip_id,owner,json.dumps(record)))
                else: con.execute('UPDATE trips SET data=? WHERE id=? AND owner=?',(json.dumps(record),trip_id,owner))
                return reply(record,'201 Created' if method == 'POST' else '200 OK')
            if path.startswith('/api/trips/') and method == 'DELETE':
                deleted = con.execute('DELETE FROM trips WHERE id=? AND owner=?',(path.rsplit('/',1)[1],owner)).rowcount
                return reply({'deleted':bool(deleted)},'200 OK' if deleted else '404 Not Found')
        return reply({'error':'Not found'},'404 Not Found')
    files = {'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css'),'/premium.css':('premium.css','text/css'),'/favicon.svg':('favicon.svg','image/svg+xml'),'/robots.txt':('robots.txt','text/plain'),'/admin':('admin.html','text/html'),'/admin.js':('admin.js','text/javascript'),'/admin.css':('admin.css','text/css')}
    files.update({'/world.js':('world.js','text/javascript'),'/world.css':('world.css','text/css'),'/city.svg':('city.svg','image/svg+xml')})
    files.update({'/countries.json':('countries.json','application/json'),'/country-photos.json':('country-photos.json','application/json')})
    # Only curated catalogue JPEGs are public; never expose a general asset directory.
    for code, photo in catalog.COUNTRY_PHOTOS.items():
        image_path = f'/assets-country/{code.lower()}.jpg'
        if code in catalog.COUNTRY_MAP and photo.get('photo') == image_path:
            files[image_path] = (image_path.lstrip('/'), 'image/jpeg')
    if path in ('/admin','/admin.js','/admin.css'):
        headers.append(('X-Robots-Tag','noindex, nofollow'))
    if path not in files or method not in ('GET','HEAD'): return reply({'error':'Not found'},'404 Not Found')
    file, mime = files[path]
    if not (ROOT / file).is_file(): return reply({'error':'Not found'},'404 Not Found')
    content = (ROOT / file).read_bytes()
    if path == '/':
        html = content.decode().replace('<!-- SEARCH_METADATA -->', search_metadata())
        # Render public destination content into the initial response for crawlers and no-JS readers.
        cards = ''.join(f'<article class="card"><div class="card-photo"><img loading="lazy" src="https://images.unsplash.com/{d["image"]}?auto=format&amp;fit=crop&amp;w=700&amp;q=80" alt="{escape(d["name"])}"><span class="card-country">{escape(d["country"])}</span></div><div class="card-body"><h3>{escape(d["name"])}</h3><p>{escape(d["tag"])}</p><div class="card-meta"><span>{d["days"]} days</span><span>est. ${d["cost"]:,}</span></div></div></article>' for d in DESTINATIONS)
        html = html.replace('<div id="destinations" class="cards" aria-live="polite"></div>',f'<div id="destinations" class="cards" aria-live="polite">{cards}</div>')
        content = html.encode()
    content_type = mime if mime == 'image/jpeg' else mime+'; charset=utf-8'
    cache_control = 'public, max-age=3600' if mime == 'image/jpeg' else 'no-cache'
    start_response(status,headers + [('Content-Type',content_type),('Content-Length',str(len(content))),('Cache-Control',cache_control)])
    return [content] if method == 'GET' else []

if __name__ == '__main__':
    port = int(os.environ.get('PORT','8080'))
    print(f'Orbit running at http://127.0.0.1:{port}',flush=True)
    make_server('127.0.0.1',port,application).serve_forever()
