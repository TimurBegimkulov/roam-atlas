import io
import os
import json
import secrets
import unittest
from unittest.mock import patch
from pathlib import Path
import app

class OrbitTests(unittest.TestCase):
    def setUp(self):
        # Never let tests connect to a hosting database inherited from the shell.
        self.environment = patch.dict(os.environ, {'DATABASE_URL': '', 'RENDER': '', 'SITE_URL': ''})
        self.environment.start()
        self.original_db = app.DB
        test_root=Path(__file__).resolve().parent/'data'/'tests'
        test_root.mkdir(parents=True,exist_ok=True)
        self.test_path=test_root/('test-'+secrets.token_hex(8)+'.sqlite3')
        app.DB=str(self.test_path)
        self.cookie=''
    def tearDown(self):
        for suffix in ('','-wal','-shm'):
            Path(str(self.test_path)+suffix).unlink(missing_ok=True)
        app.DB = self.original_db
        self.environment.stop()
    def request(self,path,method='GET',data=None,cookie=None,extra=None):
        payload=json.dumps(data).encode() if data is not None else b''
        env={'PATH_INFO':path,'REQUEST_METHOD':method,'wsgi.input':io.BytesIO(payload),'CONTENT_LENGTH':str(len(payload)),'HTTP_COOKIE':self.cookie if cookie is None else cookie,'HTTP_HOST':'localhost','HTTP_X_ORBIT_REQUEST':'1'}
        env.update(extra or {})
        response={}
        def start(status,headers):
            response.update(status=int(status.split()[0]),headers=dict(headers))
        raw=b''.join(app.application(env,start))
        if 'Set-Cookie' in response['headers'] and cookie is None:self.cookie=response['headers']['Set-Cookie'].split(';')[0]
        response['body']=json.loads(raw) if response['headers']['Content-Type'].startswith('application/json') else raw
        return response
    def trip(self,**changes):
        result=dict(title='A trip <script>',destination='kyoto',days=7,budget=1400,date='2027-05-01',notes='Café 日本',packed=[0,2],itinerary=['Arrival'])
        result.update(changes)
        return result
    def test_full_lifecycle(self):
        self.assertEqual(self.request('/api/trips')['body'],[])
        created=self.request('/api/trips','POST',self.trip())
        self.assertEqual(created['status'],201)
        id=created['body']['id']
        self.assertEqual(self.request('/api/trips')['body'][0]['notes'],'Café 日本')
        self.assertEqual(self.request('/api/trips/'+id,'PUT',self.trip(title='Changed'))['status'],200)
        self.assertEqual(self.request('/api/trips')['body'][0]['title'],'Changed')
        self.assertEqual(self.request('/api/trips/'+id,'DELETE')['status'],200)
        self.assertEqual(self.request('/api/trips')['body'],[])
    def test_visitor_isolation(self):
        id=self.request('/api/trips','POST',self.trip())['body']['id']
        self.assertEqual(self.request('/api/trips',cookie='')['body'],[])
        self.assertEqual(self.request('/api/trips/'+id,'PUT',self.trip(),cookie='')['status'],404)
        self.assertEqual(self.request('/api/trips/'+id,'DELETE',cookie='')['status'],404)
        self.assertEqual(len(self.request('/api/trips')['body']),1)
    def test_validation(self):
        for changes in [dict(days=0),dict(days=61),dict(budget=-1),dict(budget=float('nan')),dict(title='  '),dict(destination='fake'),dict(date='invalid'),dict(packed=[7]),dict(notes='x'*3001),dict(itinerary=['x'*201])]:
            with self.subTest(changes=changes):self.assertEqual(self.request('/api/trips','POST',self.trip(**changes))['status'],400)
    def test_csrf(self):
        self.assertEqual(self.request('/api/trips','POST',self.trip(),extra={'HTTP_X_ORBIT_REQUEST':''})['status'],403)
        self.assertEqual(self.request('/api/trips','POST',self.trip(),extra={'HTTP_ORIGIN':'https://evil.test'})['status'],403)
    def test_numeric_validation_does_not_truncate_days_or_accept_booleans(self):
        for changes in (dict(days=1.5), dict(days=True), dict(budget=True), dict(budget=float('inf'))):
            with self.subTest(changes=changes):
                self.assertEqual(self.request('/api/trips','POST',self.trip(**changes))['status'],400)
    def test_read_only_catalogue_never_creates_a_private_session(self):
        response = self.request('/api/countries')
        self.assertEqual(response['status'], 200)
        self.assertNotIn('Set-Cookie', response['headers'])
        countries = {country['code']: country for country in response['body']}
        self.assertIn('AQ', countries)
        self.assertNotIn('CS', countries)
        self.assertEqual(countries['AQ']['cityCount'], 0)
        page = self.request('/api/world', extra={'QUERY_STRING': 'country=AQ&page=100'})
        self.assertEqual(page['body']['page'], 1)
        self.assertEqual(page['body']['items'], [])
        self.assertNotIn('Set-Cookie', page['headers'])
    def test_static_data_allowlist_does_not_expose_private_files(self):
        self.assertEqual(self.request('/countries.json')['status'], 200)
        for path in ('/.env.example', '/database.py', '/accounts.py', '/data/orbit.sqlite3', '/cities.json.gz', '/country-photos.json/../app.py'):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)['status'], 404)
    def test_country_jpegs_are_public_with_binary_mime_and_head_support(self):
        response = self.request('/assets-country/fr.jpg')
        self.assertEqual(response['status'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'image/jpeg')
        self.assertTrue(response['body'].startswith(b'\xff\xd8'))
        self.assertEqual(int(response['headers']['Content-Length']), len(response['body']))
        head = self.request('/assets-country/fr.jpg', method='HEAD')
        self.assertEqual(head['body'], b'')
        self.assertEqual(head['headers']['Content-Length'], response['headers']['Content-Length'])
        for path in ('/assets-country/FR.jpg', '/assets-country/an.jpg', '/assets-country/zz.jpg', '/assets-country/../app.py', '/assets-country/fr.webp', '/assets-country/fr.jpg/anything'):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)['status'], 404)
    def test_static_and_traversal(self):
        home=self.request('/')
        self.assertIn(b'<html lang="en">',home['body'])
        self.assertEqual(home['status'],200)
        self.assertIn('Content-Security-Policy',home['headers'])
        self.assertEqual(self.request('/../app.py')['status'],404)
        self.assertEqual(self.request('/app.py')['status'],404)
    def test_catalog(self):
        self.assertEqual(len(self.request('/api/destinations')['body']),6)
        self.assertEqual(self.request('/api/health')['body']['status'],'ok')
    def test_public_search_metadata(self):
        with patch.dict(os.environ,{'SITE_URL':'https://roam-atlas.example','GOOGLE_SITE_VERIFICATION':'test-verification'}):
            home=self.request('/')['body'].decode()
            self.assertIn('Roam Atlas — Travel Planner',home)
            self.assertIn('rel="canonical" href="https://roam-atlas.example/"',home)
            self.assertIn('name="google-site-verification" content="test-verification"',home)
            self.assertIn('<h3>Kyoto</h3>',home)
            self.assertIn('https://roam-atlas.example/sitemap.xml',self.request('/robots.txt')['body'].decode())
            self.assertIn('<loc>https://roam-atlas.example/</loc>',self.request('/sitemap.xml')['body'].decode())
            self.assertEqual(self.request('/api/trips')['headers']['X-Robots-Tag'],'noindex, nofollow')
    def test_local_preview_not_indexable(self):
        with patch.dict(os.environ,{'SITE_URL':''}):
            self.assertIn(b'noindex,nofollow',self.request('/')['body'])
            self.assertIn(b'Disallow: /',self.request('/robots.txt')['body'])
            self.assertEqual(self.request('/sitemap.xml')['status'],503)
    def test_origin_and_verification_validation(self):
        with patch.dict(os.environ,{'SITE_URL':'https://example.com/evil?x=1','GOOGLE_SITE_VERIFICATION':'\"><script>alert(1)</script>'}):
            html=self.request('/')['body'].decode()
            self.assertNotIn('rel="canonical"',html)
            self.assertNotIn('<script>alert(1)</script>',html)
    def test_secure_cookie(self):
        self.assertIn('Secure',self.request('/api/trips',extra={'HTTP_X_FORWARDED_PROTO':'https'})['headers']['Set-Cookie'])
        self.assertIn('HttpOnly',self.request('/api/trips',cookie='')['headers']['Set-Cookie'])

if __name__=='__main__': unittest.main()
