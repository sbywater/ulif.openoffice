# tests for xmlrpc module
import filecmp
import os
import shutil
import tempfile
import unittest
import xmlrpclib
from paste.deploy import loadapp
from webob import Request
from ulif.openoffice.cachemanager import CacheManager
from ulif.openoffice.testing import WSGIXMLRPCAppTransport
from ulif.openoffice.xmlrpc import WSGIXMLRPCApplication


class ServerTestsSetup(unittest.TestCase):
    # common setup for XMLRPC server tests

    def setUp(self):
        self.src_dir = tempfile.mkdtemp()
        self.src_path = os.path.join(self.src_dir, 'sample.txt')
        open(self.src_path, 'wb').write('Hi there!\n')
        self.result_dir = None
        self.inputdir = os.path.join(os.path.dirname(__file__), 'input')
        self.paste_conf1 = os.path.join(self.inputdir, 'xmlrpcsample.ini')
        self.cachedir = os.path.join(self.src_dir, 'cache')
        self.paste_conf_tests = os.path.join(self.src_dir, 'paste.ini')
        paste_conf = open(self.paste_conf1, 'r').read().replace(
            '/tmp/mycache', self.cachedir)
        open(self.paste_conf_tests, 'w').write(paste_conf)

    def tearDown(self):
        shutil.rmtree(self.src_dir)
        if self.result_dir is not None and os.path.isdir(self.result_dir):
            shutil.rmtree(self.result_dir)


class ServerTests(ServerTestsSetup):
    # raw xmlrpc server tests

    def xmlrpc_request(self, method_name, args=()):
        # create an xmlrpcrequest
        request = Request.blank('http://localhost/RPC2')
        request.method = 'POST'
        request.content_type = 'text/xml'
        request.body = xmlrpclib.dumps(args, method_name, allow_none=True)
        return request

    def test_http_get_not_accepted(self):
        # HTTP GET is not acceptable for xmlrpc
        app = WSGIXMLRPCApplication()
        req = Request.blank('http://localhost/test.html')
        resp = req.get_response(app)
        self.assertEqual(resp.status, '400 Bad Request')

    def test_help_available(self):
        # we can request a list of messages
        app = WSGIXMLRPCApplication()
        req = self.xmlrpc_request('system.listMethods', ())
        resp = req.get_response(app)
        assert resp.body.startswith("<?xml version='1.0'?>")
        assert "<string>system.methodHelp</string>" in resp.body
        # the result can be processed by xmlrpclib
        result = xmlrpclib.loads(resp.body)
        assert isinstance(result, tuple)
        result_values, method_name = result
        assert 'convert_locally' in result_values[0]

    def test_convert_locally(self):
        # we can convert files locally
        app = WSGIXMLRPCApplication()
        req = self.xmlrpc_request(
            'convert_locally', (self.src_path, {}))
        resp = req.get_response(app)
        result = xmlrpclib.loads(resp.body)
        result_path, cache_dir, metadata = result[0][0]
        self.result_dir = os.path.dirname(result_path)   # for cleanup
        assert metadata['error'] is False

    def test_paste_deploy_loader(self):
        # we can find the xmlrpcapp via paste.deploy plugin
        app = loadapp('config:%s' % self.paste_conf1)
        assert isinstance(app, WSGIXMLRPCApplication)
        assert app.cache_dir == '/tmp/mycache'
        return

    def test_paste_deploy_options(self):
        # we can set options via paste.deploy
        app = loadapp('config:%s' % self.paste_conf_tests)
        self.assertTrue(isinstance(app, WSGIXMLRPCApplication))
        self.assertEqual(app.cache_dir, self.cachedir)
        return


class ServerProxyTests(ServerTestsSetup):
    # xmlrpcapplication tests that use an xmlrpclib.ServerProxy

    def setUp(self):
        super(ServerProxyTests, self).setUp()
        self.app = WSGIXMLRPCApplication(cache_dir=self.cachedir)
        self.proxy = xmlrpclib.ServerProxy(
            'http://admin:admin@dummy/',
            transport=WSGIXMLRPCAppTransport(self.app))

    def test_convert_locally(self):
        # we can convert docs locally
        result_path, cache_key, metadata = self.proxy.convert_locally(
            self.src_path, {})
        self.result_dir = os.path.dirname(result_path)
        assert result_path.endswith('/sample.html.zip')

    def test_convert_locally_in_list_methods(self):
        # we can list methods (and convert_locally is included)
        result = self.proxy.system.listMethods()
        assert isinstance(result, list)
        assert 'convert_locally' in result

    def test_get_cached(self):
        # we can get cached docs
        cm = CacheManager(self.cachedir)
        fake_result_path = os.path.join(self.src_dir, 'result.txt')
        open(fake_result_path, 'wb').write('The Result\n')
        key = cm.register_doc(self.src_path, fake_result_path, 'somekey')
        assert key == '2b87e29fca6ee7f1df6c1a76cb58e101_1_1'
        result_path = self.proxy.get_cached(key)
        assert result_path is not None
        assert result_path != fake_result_path
        assert filecmp.cmp(result_path, fake_result_path, shallow=False)
