import os
from unittest.mock import patch
import admin
from test_app import OrbitTests

class AdminTests(OrbitTests):
    def setUp(self):
        super().setUp()
        self.settings=patch.dict(os.environ,{'ADMIN_PASSWORD_HASH':admin.password_hash('test-only-long-password'),'ADMIN_USERNAME':'admin','SITE_URL':''})
        self.settings.start()
    def tearDown(self):
        self.settings.stop()
        super().tearDown()
    def login(self):
        return self.request('/api/admin/login','POST',dict(username='admin',password='test-only-long-password'))
    def test_admin_access_and_logout(self):
        self.assertEqual(self.request('/api/admin/overview')['status'],401)
        self.assertEqual(self.login()['status'],200)
        self.assertEqual(self.request('/api/admin/overview')['status'],200)
        self.assertEqual(self.request('/api/admin/logout','POST')['status'],200)
        self.assertEqual(self.request('/api/admin/overview')['status'],401)
    def test_admin_lockout(self):
        for _ in range(5):
            self.assertEqual(self.request('/api/admin/login','POST',dict(username='admin',password='wrong'))['status'],401)
        self.assertEqual(self.login()['status'],429)
    def test_admin_rotation_revokes(self):
        self.login()
        with patch.dict(os.environ,{'ADMIN_PASSWORD_HASH':admin.password_hash('new-test-only-password')}):
            self.assertEqual(self.request('/api/admin/overview')['status'],401)
    def test_admin_delete_requires_auth(self):
        trip=self.request('/api/trips','POST',self.trip())['body']
        self.assertEqual(self.request('/api/admin/trips/'+trip['id'],'DELETE')['status'],401)
        self.login()
        self.assertEqual(self.request('/api/admin/trips/'+trip['id'],'DELETE')['status'],200)
    def test_admin_expiry(self):
        self.login()
        with patch('admin.time.time',return_value=9999999999):
            self.assertEqual(self.request('/api/admin/overview')['status'],401)
