import hashlib
import json
import secrets
import time
from unittest.mock import patch
import app
import catalog
from test_app import OrbitTests

class AccountTests(OrbitTests):
    def register(self,name='traveler'):
        return self.register_user(name)
    def test_account_migration_and_relogin(self):
        # Legacy guest rows still exist after the upgrade; seed the old format
        # without allowing the new API to create any guest trips.
        guest_token = secrets.token_urlsafe(32)
        guest_owner = hashlib.sha256(guest_token.encode()).hexdigest()
        created = dict(self.trip(), id=secrets.token_hex(12))
        with app.connect() as con:
            con.execute('INSERT INTO visitors VALUES (?)', (guest_owner,))
            con.execute('INSERT INTO trips VALUES (?,?,?)', (created['id'], guest_owner, json.dumps(created)))
        self.cookie = 'orbit_session=' + guest_token
        for path, method, data in (('/api/trips', 'GET', None), ('/api/trips', 'POST', self.trip()), ('/api/trips/'+created['id'], 'PUT', self.trip(title='Unauthorized')), ('/api/trips/'+created['id'], 'DELETE', None)):
            with self.subTest(method=method):
                self.assert_authentication_required(self.request(path, method, data))
        with app.connect() as con:
            row = con.execute('SELECT owner,data FROM trips WHERE id=?', (created['id'],)).fetchone()
            self.assertEqual(row['owner'], guest_owner)
            self.assertEqual(json.loads(row['data']), created)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM visitors').fetchone()[0], 1)
        self.assertEqual(self.register()['status'],200)
        self.assertEqual(self.request('/api/trips')['body'][0]['id'],created['id'])
        self.assertEqual(self.request('/api/account')['body']['user']['username'],'traveler')
        with app.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM trips WHERE owner=?', (guest_owner,)).fetchone()[0], 0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM trips').fetchone()[0], 1)
        self.request('/api/account/logout','POST',{})
        self.assertIsNone(self.request('/api/account')['body']['user'])
        self.assert_authentication_required(self.request('/api/trips'))
        self.assertEqual(self.request('/api/account/login','POST',{'username':'traveler','password':'a-long-test-password-42'})['status'],200)
        self.assertEqual(self.request('/api/trips')['body'][0]['id'],created['id'])
    def test_account_isolation_and_expiry(self):
        self.register()
        created = self.request('/api/trips','POST',self.trip())['body']
        first_cookie = self.cookie
        self.cookie='';self.register('other_traveler')
        self.assertEqual(self.request('/api/trips')['body'],[])
        self.cookie=first_cookie
        with patch('accounts.time.time',return_value=time.time()+31*86400):
            for path, method, data in (('/api/trips', 'GET', None), ('/api/trips', 'POST', self.trip()), ('/api/trips/'+created['id'], 'PUT', self.trip(title='Unauthorized')), ('/api/trips/'+created['id'], 'DELETE', None)):
                with self.subTest(method=method):
                    self.assert_authentication_required(self.request(path, method, data))
            self.assertIsNone(self.request('/api/account')['body']['user'])
        self.assertEqual(self.request('/api/account/login','POST',{'username':'traveler','password':'a-long-test-password-42'})['status'],200)
        self.assertEqual(self.request('/api/trips')['body'], [created])
        with app.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM visitors').fetchone()[0], 0)
    def test_account_validation_csrf_and_lockout(self):
        self.assertEqual(self.request('/api/account/register','POST',{'username':'x','password':'short'})['status'],400)
        self.assertEqual(self.request('/api/account/register','POST',{},extra={'HTTP_ORIGIN':'https://evil.test'})['status'],403)
        self.register()
        for _ in range(10):
            self.assertEqual(self.request('/api/account/login','POST',{'username':'traveler','password':'incorrect-but-long'})['status'],401)
        self.assertEqual(self.request('/api/account/login','POST',{'username':'traveler','password':'a-long-test-password-42'})['status'],429)
    def test_other_account_cannot_mutate_a_trip_and_logout_revokes_session(self):
        self.register('first_traveler')
        created = self.request('/api/trips', 'POST', self.trip())['body']
        owner_cookie = self.cookie
        self.cookie = ''
        self.register('second_traveler')
        self.assertEqual(self.request('/api/trips/'+created['id'], 'PUT', self.trip(title='Unauthorized'))['status'], 404)
        self.assertEqual(self.request('/api/trips/'+created['id'], 'DELETE')['status'], 404)
        self.cookie = owner_cookie
        self.assertEqual(self.request('/api/trips')['body'][0]['title'], created['title'])
        self.request('/api/account/logout', 'POST', {})
        self.assertIsNone(self.request('/api/account', cookie=owner_cookie)['body']['user'])
        for path, method, data in (('/api/trips', 'GET', None), ('/api/trips', 'POST', self.trip()), ('/api/trips/'+created['id'], 'PUT', self.trip(title='Unauthorized')), ('/api/trips/'+created['id'], 'DELETE', None)):
            with self.subTest(method=method):
                self.assert_authentication_required(self.request(path, method, data, cookie=owner_cookie))
    def test_world_search_and_trip(self):
        paris=catalog.search('q=Paris&country=FR')['items'][0]
        self.assertEqual(paris['name'],'Paris')
        self.assertGreater(catalog.search('q=Франция')['total'],0)
        self.assertGreater(len(catalog.CITIES),30000)
        self.register()
        result=self.request('/api/trips','POST',self.trip(destination=paris['id']))
        self.assertEqual(result['status'],201)
        self.assertEqual(self.request('/api/trips')['body'][0]['destinationInfo']['name'],'Paris')
