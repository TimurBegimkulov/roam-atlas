import time
from unittest.mock import patch
import catalog
from test_app import OrbitTests

class AccountTests(OrbitTests):
    def register(self,name='traveler'):
        return self.request('/api/account/register','POST',{'username':name,'password':'a-long-test-password-42'})
    def test_account_migration_and_relogin(self):
        created=self.request('/api/trips','POST',self.trip())['body']
        self.assertEqual(self.register()['status'],200)
        self.assertEqual(self.request('/api/trips')['body'][0]['id'],created['id'])
        self.assertEqual(self.request('/api/account')['body']['user']['username'],'traveler')
        self.request('/api/account/logout','POST',{})
        self.assertIsNone(self.request('/api/account')['body']['user'])
        self.assertEqual(self.request('/api/trips')['body'],[])
        self.request('/api/account/login','POST',{'username':'traveler','password':'a-long-test-password-42'})
        self.assertEqual(self.request('/api/trips')['body'][0]['id'],created['id'])
    def test_account_isolation_and_expiry(self):
        self.register();self.request('/api/trips','POST',self.trip());first_cookie=self.cookie
        self.cookie='';self.register('other_traveler')
        self.assertEqual(self.request('/api/trips')['body'],[])
        self.cookie=first_cookie
        with patch('accounts.time.time',return_value=time.time()+31*86400):
            self.assertIsNone(self.request('/api/account')['body']['user'])
    def test_account_validation_csrf_and_lockout(self):
        self.assertEqual(self.request('/api/account/register','POST',{'username':'x','password':'short'})['status'],400)
        self.assertEqual(self.request('/api/account/register','POST',{},extra={'HTTP_ORIGIN':'https://evil.test'})['status'],403)
        self.register()
        for _ in range(10):
            self.assertEqual(self.request('/api/account/login','POST',{'username':'traveler','password':'incorrect-but-long'})['status'],401)
        self.assertEqual(self.request('/api/account/login','POST',{'username':'traveler','password':'a-long-test-password-42'})['status'],429)
    def test_world_search_and_trip(self):
        paris=catalog.search('q=Paris&country=FR')['items'][0]
        self.assertEqual(paris['name'],'Paris')
        self.assertGreater(catalog.search('q=Франция')['total'],0)
        self.assertGreater(len(catalog.CITIES),30000)
        result=self.request('/api/trips','POST',self.trip(destination=paris['id']))
        self.assertEqual(result['status'],201)
        self.assertEqual(self.request('/api/trips')['body'][0]['destinationInfo']['name'],'Paris')
