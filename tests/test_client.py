# tests for client module
import filecmp
import os
import pytest
import shutil
import tempfile
import unittest
from ulif.openoffice.client import convert_doc, Client, main
from ulif.openoffice.options import ArgumentParserError
from ulif.openoffice.testing import ConvertLogCatcher


class ClientTestsSetup(unittest.TestCase):
    # a setup for client tests
    def setUp(self):
        self.rootdir = tempfile.mkdtemp()
        self.srcdir = os.path.join(self.rootdir, 'src')
        os.mkdir(self.srcdir)
        self.cachedir = os.path.join(self.rootdir, 'cache')
        os.mkdir(self.cachedir)
        self.resultdir = None
        self.src_doc = os.path.join(self.srcdir, 'sample.txt')
        open(self.src_doc, 'w').write('Hi there.')
        self.entry_wd = os.getcwd()
        self.log_catcher = ConvertLogCatcher()

    def tearDown(self):
        try:
            if os.getcwd() != self.entry_wd:
                os.chdir(self.entry_wd)
        except OSError:
            # might happen if resultdir was deleted already
            os.chdir(self.entry_wd)
        shutil.rmtree(self.rootdir)
        if self.resultdir is not None:
            shutil.rmtree(self.resultdir)


class ConvertDocTests(ClientTestsSetup):
    # tests for convert_doc function

    def test_nocache(self):
        # by default we get a zip'd HTML representation
        result_path, cache_key, metadata = convert_doc(
            self.src_doc, options={}, cache_dir=None)
        assert 'Cmd result: 0' in self.log_catcher.get_log_messages()
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-16:] == '/sample.html.zip'
        assert cache_key is None  # no cache, no cache_key
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_cached(self):
        # with a cache_dir, the result is cached
        result_path, cache_key, metadata = convert_doc(
            self.src_doc, options={}, cache_dir=self.cachedir)
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-16:] == '/sample.html.zip'
        # cache keys are same for equal input files
        assert cache_key == '164dfcf01584bd0e3595b62fb53cf12c_1_1'
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_options(self):
        # options given are respected
        options = {'meta-procord': 'unzip,oocp',
                   'oocp-out-fmt': 'pdf'}
        result_path, cache_key, metadata = convert_doc(
            self.src_doc, options=options, cache_dir=None)
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-11:] == '/sample.pdf'
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_basename_only_input(self):
        # also source paths with a basename only are accepted
        options = {'meta-procord': 'oocp',
                   'oocp-out-fmt': 'pdf'}
        # change to the dir where the src doc resides (set back by teardown)
        os.chdir(os.path.dirname(self.src_doc))
        result_path, cache_key, metadata = convert_doc(
            os.path.basename(self.src_doc), options=options, cache_dir=None)
        assert 'Cmd result: 0' in self.log_catcher.get_log_messages()
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-11:] == '/sample.pdf'
        assert metadata == {'error': False, 'oocp_status': 0}
        # the original source doc still exists
        assert os.path.exists(self.src_doc)


class ClientTests(ClientTestsSetup):
    # tests for API Client

    def test_convert(self):
        client = Client()
        result_path, cache_key, metadata = client.convert(self.src_doc)
        self.resultdir = os.path.dirname(result_path)  # for cleanup
        assert result_path[-16:] == '/sample.html.zip'
        assert os.path.isfile(result_path)
        assert cache_key is None  # no cache, no cache_key
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_get_cached_no_file(self):
        # when asking for cached files we cope with nonexistent docs
        client = Client(cache_dir=self.cachedir)
        assert client.get_cached(
            '164dfcf01584bd0e3595b62fb53cf12c_1_1') is None

    def test_get_cached_no_cache_dir(self):
        # when asking for cached files we cope with no cache dirs
        client = Client()
        assert client.get_cached(
            '164dfcf01584bd0e3595b62fb53cf12c_1_1') is None

    def test_get_cached(self):
        # we can get an already cached doc
        client = Client(cache_dir=self.cachedir)
        result_path, cache_key, metadata = client.convert(self.src_doc)
        self.resultdir = os.path.dirname(result_path)  # for cleanup
        assert cache_key == '164dfcf01584bd0e3595b62fb53cf12c_1_1'
        cached_path = client.get_cached(cache_key)
        assert filecmp.cmp(result_path, cached_path, shallow=False)
        assert self.cachedir in cached_path

    def test_options(self):
        # we can pass in options
        client = Client()
        options = {'oocp-out-fmt': 'pdf', 'meta-procord': 'oocp'}
        result_path, cache_key, metadata = client.convert(
            self.src_doc, options=options)
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-11:] == '/sample.pdf'
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_argument_error(self):
        # wrong args lead to ArgumentErrors
        client = Client()
        options = {'oocp-out-fmt': 'foo', 'meta-procord': 'foo,bar'}
        self.assertRaises(
            ArgumentParserError,
            client.convert, self.src_doc, options=options)

    def test_get_cached_by_source_no_file(self):
        # we cannot get a cached file not cached before
        client = Client(cache_dir=self.cachedir)
        cached_path, cache_key = client.get_cached_by_source(self.src_doc)
        assert cached_path is None
        assert cache_key is None

    def test_get_cached_by_source_no_cache_dir(self):
        # we cannot get a cached file if w/o cache_dir set
        client = Client()
        cached_path, cache_key = client.get_cached_by_source(self.src_doc)
        assert cached_path is None
        assert cache_key is None

    def test_get_cached_by_source(self):
        # we can get a file when cached and by source/options
        client = Client(cache_dir=self.cachedir)
        result_path, cache_key, metadata = client.convert(self.src_doc)
        self.resultdir = os.path.dirname(result_path)  # for cleanup
        assert cache_key == '164dfcf01584bd0e3595b62fb53cf12c_1_1'
        cached_path, cache_key = client.get_cached_by_source(self.src_doc)
        assert filecmp.cmp(result_path, cached_path, shallow=False)
        assert self.cachedir in cached_path
        assert cache_key == '164dfcf01584bd0e3595b62fb53cf12c_1_1'


class MainClientTests(ClientTestsSetup):
    # tests for the client modules `main` function

    @pytest.fixture(autouse=True)
    def mycapsys(self, capsys):
        self.mycapsys = capsys

    def test_convert_regular(self):
        # we can do a regular conversion
        main([
              '-meta-procord', 'oocp',
              '-oocp-out-fmt', 'pdf',
              self.src_doc])
        out, err = self.mycapsys.readouterr()
        #out = ''.join(eval(out))  # strange format from py.test capsys
        outfile_path = out[10:-1]
        self.resultdir = os.path.dirname(outfile_path)   # for cleanup
        assert out.startswith('RESULT in')
        assert os.path.exists(outfile_path)
        assert os.path.isfile(outfile_path)
        assert outfile_path.endswith('/sample.pdf')

    def test_help(self):
        # we can get help
        try:
            main(['--help'])
        except SystemExit:
            pass  # help causes sys.exit(1)
        out, err = self.mycapsys.readouterr()
        assert out[:43] == u"usage: oooclient [-h] [--cachedir CACHEDIR]"

    def test_argument_error(self):
        # argument errors are shown and explained
        try:
            main(['--not-existing-arg', self.src_doc])
        except SystemExit:
            pass  # errors cause sys.exit()
        out, err = self.mycapsys.readouterr()
        assert err.endswith(
            'error: unrecognized arguments: --not-existing-arg\n')
