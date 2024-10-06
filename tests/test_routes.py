"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
import random
from unittest import TestCase
from tests.factories import AccountFactory
from service import talisman
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...

    # Testing Read Account for both happy and sad path
    def test_read_account(self):
        """It should Read and Account when sending an account id"""
        accounts = self._create_accounts(2)

        response = self.client.get(f"{BASE_URL}/{accounts[1].id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(accounts[1].serialize(), response.get_json())

    def test_read_account_failed(self):
        """It should return 404 when an invalid ID is requested"""
        accounts = self._create_accounts(2)
        while True:
            id = random.randint(0, 100)
            if id not in (account.id for account in accounts):
                break

        response = self.client.get(f"{BASE_URL}/{id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Test List Account
    def test_list_accounts(self):
        """It should return a list of all the accounts"""
        num_accts = random.randint(3, 9)
        self._create_accounts(num_accts)
        response = self.client.get(BASE_URL)
        list_accts = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_accts), num_accts)

    # Test update an Account
    def test_update_accout(self):
        """It should update Account 1 to new information"""
        accounts = self._create_accounts(2)
        new_acct = AccountFactory()
        new_acct_json = new_acct.serialize()

        id = accounts[1].id
        response = self.client.put(f"{BASE_URL}/{id}", json=new_acct_json)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_acct_json = response.get_json()
        for key in new_acct_json:
            if not key == "id":
                self.assertEqual(new_acct_json[key], updated_acct_json[key])

    # Test update failed with ID not exists
    def test_update_no_id(self):
        """Update: it should return with ID not found error"""
        accounts = self._create_accounts(9)
        new_acct = AccountFactory()
        new_acct_json = new_acct.serialize()

        while True:
            id = random.randint(0, 100)
            if id not in (account.id for account in accounts):
                break

        response = self.client.put(f"{BASE_URL}/{id}", json=new_acct_json)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Test update failed with invalid data
    def test_update_invalid_data(self):
        """It should return DataValidation error"""
        accounts = self._create_accounts(9)
        new_acct = AccountFactory()
        new_acct_json = new_acct.serialize()

        # this should raise a type error
        response = self.client.put(f"{BASE_URL}/{accounts[1].id}", json=[])
        app.logger.info(f"got error {response.data}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # this should raise a key error
        del new_acct_json["email"]
        response = self.client.put(f"{BASE_URL}/{accounts[1].id}", json=new_acct_json)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # test delete an Account with give ID
    def test_delete_account(self):
        """It should delete the account with the ID"""
        num_account = random.randint(2, 9)
        accounts = self._create_accounts(num_account)
        select = random.randint(1, num_account-1)
        id_2_delete = accounts[select].id

        response = self.client.delete(f"{BASE_URL}/{id_2_delete}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(BASE_URL)
        accts = response.get_json()
        self.assertEqual(len(accts), num_account-1)

    # Test delete failed with ID not exists
    def test_delete_no_id(self):
        """Delete: it should return with ID not found error"""
        self._create_accounts(2)

        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # test error handler
    def test_method_not_allowed(self):
        """It should not allow an illegal method call"""
        response = self.client.delete(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # test secure header
    def test_secure_header(self):
        """It should return secure header"""
        secure_header = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }

        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in secure_header.items():
            self.assertEqual(response.headers.get(key), value)

    # test CORS policy implemented
    def test_cores(self):
        """It should return header with CORS policy"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), '*')
