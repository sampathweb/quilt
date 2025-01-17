from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
import responses
from ruamel.yaml import YAML

import quilt3 as he
from quilt3 import util

from .utils import QuiltTestCase

DEFAULT_URL = 'https://registry.example.com'


class TestAPI(QuiltTestCase):
    def test_config(self):
        content = {
            'navigator_url': 'https://foo.bar',
            'elastic_search_url': 'https://es.foo',
            'accept_invalid_config_keys': 'yup',
            'telemetry_disabled': False
        }
        self.requests_mock.add(responses.GET, 'https://foo.bar/config.json', json=content, status=200)

        he.config('https://foo.bar')

        yaml = YAML()
        config = yaml.load(util.CONFIG_PATH)

        # These come from CONFIG_TEMPLATE, not the mocked config file.
        content['default_local_registry'] = util.BASE_PATH.as_uri() + '/packages'
        content['default_remote_registry'] = None
        content['default_install_location'] = None
        content['registryUrl'] = None

        assert config == content

    def test_config_invalid_host(self):
        # Our URL handling is very forgiving, since we might receive a host
        # defined in local DNS, like 'foo' instead of 'foo.com' -- and on top
        # of that, we automatically add 'https://' to the name if no schema is
        # present.  ..but, a bad port causes an error..
        with pytest.raises(util.QuiltException, match='Port must be a number'):
            he.config('https://fliff:fluff')

    def test_empty_list_role(self):
        empty_list_response = { 'results': [] }
        self.requests_mock.add(responses.GET, DEFAULT_URL + '/api/roles',
                json=empty_list_response, status=200)
        assert he.admin.list_roles() == []

    def test_list_role(self):
        result = {
            'name': 'test',
            'arn': 'asdf123',
            'id': '1234-1234'
        }
        list_response = { 'results': [result] }
        self.requests_mock.add(responses.GET, DEFAULT_URL + '/api/roles',
                json=list_response, status=200)
        assert he.admin.list_roles() == [result]

    def test_get_role(self):
        result = {
            'name': 'test',
            'arn': 'asdf123',
            'id': '1234-1234'
        }
        self.requests_mock.add(responses.GET, DEFAULT_URL + '/api/roles/1234-1234',
                json=result, status=200)
        assert he.admin.get_role('1234-1234') == result

    def test_create_role(self):
        result = {
            'name': 'test',
            'arn': 'asdf123',
            'id': '1234-1234'
        }
        self.requests_mock.add(responses.POST, DEFAULT_URL + '/api/roles',
                json=result, status=200)
        assert he.admin.create_role('test', 'asdf123') == result

    def test_edit_role(self):
        get_result = {
            'name': 'test',
            'arn': 'asdf123',
            'id': '1234-1234'
        }
        result = {
            'name': 'test_new_name',
            'arn': 'qwer456',
            'id': '1234-1234'
        }
        self.requests_mock.add(responses.GET, DEFAULT_URL + '/api/roles/1234-1234',
                json=get_result, status=200)
        self.requests_mock.add(responses.PUT, DEFAULT_URL + '/api/roles/1234-1234',
                json=result, status=200)
        assert he.admin.edit_role('1234-1234', 'test_new_name', 'qwer456') == result

    def test_delete_role(self):
        self.requests_mock.add(responses.DELETE, DEFAULT_URL + '/api/roles/1234-1234',
                status=200)
        he.admin.delete_role('1234-1234')

    def test_set_role(self):
        self.requests_mock.add(responses.POST, DEFAULT_URL + '/api/users/set_role',
                json={}, status=200)

        not_found_result = {
            'message': "No user exists by the provided name."
        }
        self.requests_mock.add(responses.POST, DEFAULT_URL + '/api/users/set_role',
                json=not_found_result, status=400)

        he.admin.set_role('test_user', 'test_role')

        with pytest.raises(util.QuiltException):
            he.admin.set_role('not_found', 'test_role')
