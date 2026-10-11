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
        test_root=Path(__file__).resolve().parent/'data'/'tests'
        test_root.mkdir(parents=True,exist_ok=True)
        self.test_path=test_root/('test-'+secrets.token_hex(8)+'.sqlite3')
        app.DB=str(self.test_path)
        self.cookie=''
    def tearDown(self):
        for suffix in ('','-wal','-shm'):
            Path(str(self.test_path)+suffix).unlink(missing_ok=True)
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
