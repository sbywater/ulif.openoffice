# -*- coding: utf-8 -*-
#
# tests for wsgi module
#
# Copyright (C) 2011, 2013, 2015-2016 Uli Fouquet
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
import pytest
import zipfile
from paste.deploy import loadapp
from webob import Request
from ulif.openoffice.cachemanager import get_marker
from ulif.openoffice.wsgi import (
    RESTfulDocConverter, FileIterator, FileIterable, get_mimetype
    )

pytestmark = pytest.mark.wsgi


@pytest.fixture(scope="function")
def iter_path(tmpdir):
    """Return the path of a tmp file containung "0123456789".

    Value is for testing file iterables and file iterators.
    """
    tmpdir.join("iter.test").write(b"0123456789")
    return str(tmpdir.join("iter.test"))


def is_zipfile_with_file(workdir, content, filename="sample.html"):
    """Assert that `content` contains a zipfile containing `filename`.

    `workdir` should be a `py.local` path where we can create files in.
    """
    content_file = workdir / "myresult.zip"
    content_file.write_binary(content)
    assert zipfile.is_zipfile(str(content_file))
    return filename in zipfile.ZipFile(str(content_file), "r").namelist()


class TestGetMimetype(object):
    # tests for get_mimetype()
    def test_nofilename(self):
        assert get_mimetype(None) == 'application/octet-stream'

    def test_nofile(self):
        assert get_mimetype('not-a-file') == 'application/octet-stream'

    def test_txtfile(self):
        assert get_mimetype('file.txt') == 'text/plain'

    def test_jpgfile(self):
        assert get_mimetype('file.jpg') == 'image/jpeg'

    def test_zipfile(self):
        assert get_mimetype('file.zip') == 'application/zip'

    def test_unknownfile(self):
        assert get_mimetype('unknown.type') == 'application/octet-stream'


class TestFileIterator(object):

    def test_empty_file(self, tmpdir):
        tmpdir.join("iter.test").write("")
        fi = FileIterator(str(tmpdir / "iter.test"), None, None)
        with pytest.raises(StopIteration):
            next(iter(fi))

    def test_start(self, iter_path):
        fi = FileIterator(iter_path, 4, None)
        assert b'456789' == next(fi)
        with pytest.raises(StopIteration):
            next(fi)

    def test_stop(self, iter_path):
        fi = FileIterator(iter_path, 0, 4)
        assert b'0123' == next(fi)
        with pytest.raises(StopIteration):
            next(fi)

    def test_start_and_stop(self, iter_path):
        fi = FileIterator(iter_path, 2, 6)
        assert b'2345' == next(fi)
        with pytest.raises(StopIteration):
            next(fi)

    def test_multiple_reads(self, iter_path):
        block = b'x' * FileIterator.chunk_size
        with open(iter_path, 'wb') as fd:
            fd.write(2 * block)
        fi = FileIterator(iter_path)
        assert block == next(fi)
        assert block == next(fi)
        with pytest.raises(StopIteration):
            next(fi)

    def test_start_bigger_than_end(self, iter_path):
        fi = FileIterator(iter_path, 2, 1)
        with pytest.raises(StopIteration):
            next(fi)

    def test_end_is_zero(self, iter_path):
        fi = FileIterator(iter_path, 0, 0)
        with pytest.raises(StopIteration):
            next(fi)


class TestFileIterable(object):

    def test_range(self, iter_path):
        fi = FileIterable(iter_path)
        assert [b'234'] == list(fi.app_iter_range(2, 5))
        assert [b'67'] == list(fi.app_iter_range(6, 8))


class TestDocConverterFunctional(object):

    def test_restful_doc_converter(self):
        # we can create a RESTful sample app
        app = RESTfulDocConverter()
        req = Request.blank('http://localhost/test.html')
        resp = app(req)
        assert resp.status == "404 Not Found"

    def test_restful_doc_converter_simple_get(self):
        # RESTful sample app handles simple GET
        app = RESTfulDocConverter()
        req = Request.blank('http://localhost/docs')
        resp = app(req)
        req = Request.blank('http://localhost/docs')
        resp = app(req)
        assert resp.status == "200 OK"

    def test_paste_deploy_loader(self, conv_env):
        # we can find the docconverter via paste.deploy plugin
        app = loadapp('config:%s' % (conv_env / "sample1.ini"))
        assert isinstance(app, RESTfulDocConverter)
        assert app.cache_dir is None

    def test_paste_deploy_options(self, conv_env):
        # we can set options via paste.deploy
        app = loadapp('config:%s' % (conv_env / "paste.ini"))
        assert isinstance(app, RESTfulDocConverter)
        assert app.cache_dir == str(conv_env / "cache")

    def test_new(self, conv_env):
        # we can get a form for sending new docs
        app = RESTfulDocConverter(cache_dir=str(conv_env / "cache"))
        req = Request.blank('http://localhost/docs/new')
        resp = app(req)
        assert resp.headers['Content-Type'] == 'text/html; charset=UTF-8'
        assert b'action="/docs"' in resp.body

    def test_create_with_cache(self, conv_env):
        # we can trigger conversions that will be cached
        app = RESTfulDocConverter(cache_dir=str(conv_env / "cache"))
        req = Request.blank(
            'http://localhost/docs',
            POST=dict(doc=('sample.txt', 'Hi there!'),
                      CREATE='Send',
                      )
            )
        resp = app(req)
        # we get a location header
        assert resp.headers['Location'] == (
            'http://localhost:80/docs/396199333edbf40ad43e62a1c1397793_1_1')
        assert resp.status == "201 Created"
        assert resp.headers['Content-Type'] == 'application/zip'
        assert is_zipfile_with_file(conv_env, resp.body)

    def test_create_without_cache(self, conv_env):
        # we can convert docs without cache but won't get a GET location
        app = RESTfulDocConverter(cache_dir=None)
        req = Request.blank(
            'http://localhost/docs',
            POST=dict(doc=('sample.txt', 'Hi there!'),
                      CREATE='Send',
                      )
            )
        resp = app(req)
        assert "Location" not in resp.headers
        # instead of 201 Created we get 200 Ok
        assert resp.status.lower() == "200 ok"
        assert resp.headers["Content-Type"] == "application/zip"
        assert is_zipfile_with_file(conv_env, resp.body)

    def test_create_out_fmt_respected(self, conv_env):
        # a single out_fmt option will result in appropriate output format
        # (the normal option name would be 'oocp.out_fmt')
        app = RESTfulDocConverter(cache_dir=str(conv_env / "cache"))
        myform = dict(
            doc=('sample.txt', 'Hi there!'),
            CREATE='Send', out_fmt='pdf',
            )
        req = Request.blank('http://localhost/docs', POST=myform)
        resp = app(req)
        # we get a location header
        assert resp.headers["Location"] == (
            'http://localhost:80/docs/396199333edbf40ad43e62a1c1397793_1_1')
        assert resp.status == "201 Created"
        assert resp.headers['Content-Type'] == 'application/zip'
        assert is_zipfile_with_file(
            conv_env, resp.body, filename="sample.pdf")

    def test_show_yet_uncached_doc(self, conv_env):
        # a yet uncached doc results in 404
        app = RESTfulDocConverter(cache_dir=str(conv_env / "cache"))
        url = 'http://localhost/docs/NOT-A-VALID-DOCID'
        resp = app(Request.blank(url))
        assert resp.status == "404 Not Found"

    def test_show_with_cache(self, conv_env):
        # we can retrieve cached files
        app = RESTfulDocConverter(cache_dir=str(conv_env / "cache"))
        conv_env.join("sample_in.txt").write("Fake source.")
        conv_env.join("sample_out.pdf").write("Fake result.")
        marker = get_marker(dict(foo='bar', bar='baz'))
        doc_id = app.cache_manager.register_doc(
            source_path=str(conv_env.join("sample_in.txt")),
            to_cache=str(conv_env.join("sample_out.pdf")),
            repr_key=marker)
        assert doc_id == '3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1_1'
        url = 'http://localhost/docs/3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1_1'
        req = Request.blank(url)
        resp = app(req)
        assert resp.status == "200 OK"
        assert resp.content_type == "application/pdf"
