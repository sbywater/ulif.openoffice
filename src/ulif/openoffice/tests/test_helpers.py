# -*- coding: utf-8 -*-
##
## test_helpers.py
## Login : <uli@pu.smp.net>
## Started on  Mon May  2 00:53:37 2011 Uli Fouquet
## $Id$
## 
## Copyright (C) 2011 Uli Fouquet
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##
import os
import shutil
import tempfile
import unittest
import zipfile
from ulif.openoffice.processor import OOConvProcessor
from ulif.openoffice.helpers import (
    copy_to_secure_location, get_entry_points, unzip, zip, remove_file_dir,
    extract_css, cleanup_html,)

class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None
        return

    def tearDown(self):
        shutil.rmtree(self.workdir)
        path = self.resultpath
        if isinstance(path, basestring):
            if os.path.isfile(path):
                path = os.path.dirname(path)
            shutil.rmtree(path)
        return

    def test_copy_to_secure_location_file(self):
        sample_path = os.path.join(self.workdir, 'sample.txt')
        open(sample_path, 'wb').write("Hi from sample")
        self.resultpath = copy_to_secure_location(sample_path)
        assert os.path.isfile(os.path.join(self.resultpath, 'sample.txt'))

    def test_copy_to_secure_location_path(self):
        sample_path = os.path.join(self.workdir, 'sample.txt')
        open(sample_path, 'wb').write("Hi from sample")
        sample_dir = os.path.dirname(sample_path)
        self.resultpath = copy_to_secure_location(sample_dir)
        assert os.path.isfile(os.path.join(self.resultpath, 'sample.txt'))

    def test_get_entry_points(self):
        result = get_entry_points('ulif.openoffice.processors')
        assert result['oocp'] is OOConvProcessor

    def test_unzip(self):
        # make sure we can unzip filetrees
        zipfile = os.path.join(self.workdir, 'sample.zip')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample1.zip'),
            zipfile)
        dst = os.path.join(self.workdir, 'dst')
        os.mkdir(dst)
        unzip(zipfile, dst)
        assert os.listdir(dst) == ['somedir']
        level2_dir = os.path.join(dst, 'somedir')
        assert os.listdir(level2_dir) == ['sample.txt', 'othersample.txt']

    def test_zip_file(self):
        # make sure we can zip single files
        new_dir = os.path.join(self.workdir, 'sampledir')
        os.mkdir(new_dir)
        sample_file = os.path.join(new_dir, 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.resultpath = zip(sample_file)
        assert zipfile.is_zipfile(self.resultpath)

    def test_zip_dir(self):
        # make sure we can zip complete dir trees
        new_dir = os.path.join(self.workdir, 'sampledir')
        os.mkdir(new_dir)
        os.mkdir(os.path.join(new_dir, 'subdir1'))
        os.mkdir(os.path.join(new_dir, 'subdir2'))
        os.mkdir(os.path.join(new_dir, 'subdir2', 'subdir21'))
        sample_file = os.path.join(new_dir, 'subdir2', 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.resultpath = zip(new_dir)
        zip_file = zipfile.ZipFile(self.resultpath, 'r')
        result = sorted(zip_file.namelist())
        assert result == ['subdir1/', 'subdir2/', 'subdir2/sample.txt',
                          'subdir2/subdir21/']
        assert zip_file.testzip() is None

    def test_remove_file_dir_none(self):
        assert remove_file_dir(None) is None

    def test_remove_file_dir_non_path(self):
        assert remove_file_dir(object()) is None

    def test_remove_file_dir_not_existiing(self):
        assert remove_file_dir('not-existing-path') is None

    def test_remove_file_dir_file(self):
        # When we remove a file, also the containung dir is removed
        sample_path = os.path.join(self.workdir, 'sampledir')
        sample_file = os.path.join(sample_path, 'sample.txt')
        os.mkdir(sample_path)
        open(sample_file, 'wb').write('Hi!')
        remove_file_dir(sample_file)
        assert os.path.exists(self.workdir) is True
        assert os.path.exists(sample_path) is False

    def test_remove_file_dir_dir(self):
        sample_path = os.path.join(self.workdir, 'sampledir')
        sample_file = os.path.join(sample_path, 'sample.txt')
        os.mkdir(sample_path)
        open(sample_file, 'wb').write('Hi!')
        remove_file_dir(sample_path)
        assert os.path.exists(self.workdir) is True
        assert os.path.exists(sample_path) is False

    def test_extract_css(self):
        """

        >> from ulif.openoffice.helpers import extract_css
        >> html, css = extract_css(u'''
        ... <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        ... "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        ... <html xmlns="http://www.w3.org/1999/xhtml">
        ... <head>
        ... <meta name="generator" content="HTML Tidy for Linux/x86" />
        ... <meta http-equiv="CONTENT-TYPE" content="text/html;
        ...       charset=utf-8" />
        ...          <title>
        ...          </title>
        ...          <meta name="GENERATOR"
        ...                content="OpenOffice.org 2.4 (Linux)" />
        ...          <style type="text/css">
        ...           /* <![CDATA[ */
        ...            @page { size: 21cm 29.7cm; margin: 2cm }
        ...            p { margin-bottom: 0.21cm }
        ...            span.c2 {font-family: DejaVu Sans Mono, sans-serif}
        ...            p.c1 {margin-bottom: 0cm}
        ...           /* ]]> */
        ...          </style>
        ...         </head>
        ...         <body lang="de-DE" dir="ltr" xml:lang="de-DE">
        ...         </body>
        ...        </html>
        ... ''', 'sample.html')

      The returned css part contains all styles from input:

        >> print css
        @page { size: 21cm 29.7cm; margin: 2cm }
        p { margin-bottom: 0.21cm }
        span.c2 {font-family: DejaVu Sans Mono, sans-serif}
        p.c1 {margin-bottom: 0cm}

      The returned HTML part has the styles replaced with a link:

        >> print html # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
         <html xmlns="http://www.w3.org/1999/xhtml">
          <head>
           <meta name="generator" content="HTML Tidy for Linux/x86" />
           <meta http-equiv="CONTENT-TYPE" content="text/html;
               charset=utf-8" />
           <title>
           </title>
          <meta name="GENERATOR" content="OpenOffice.org 2.4 (Linux)" />
          <link rel="stylesheet" type="text/css" href="sample.css" />
         </head>
         <body lang="de-DE" dir="ltr" xml:lang="de-DE">
         </body>
        </html>

        """

    def test_extract_css_trash(self):
        # Also trashy docs can be handled
        result, css = extract_css("", 'sample.html')
        assert css is None
        assert result == ""

    def test_extract_css_simple(self):
        result, css = extract_css(
            "<style>a, b</style>", 'sample.html')
        link = '<link rel="stylesheet" type="text/css" '
        link += 'href="sample.css" />\n'
        assert css == 'a, b'
        assert result == link

    def test_extract_css_empty_styles1(self):
        # Also trashy docs can be handled
        result, css = extract_css(
            "<style></style>", 'sample.html')
        assert css is None
        assert result == ""

    def test_extract_css_empty_styles2(self):
        # Also trashy docs can be handled
        result, css = extract_css(
            "<html><style /></html>", 'sample.html')
        assert css is None
        assert result == "<html>\n</html>"

    def test_extract_css_nested_styles(self):
        # Trash in, trash out...
        result, css = extract_css(
            "<html><style>a<style>b</style></style></html>", 'sample.html')
        assert css == u'a\nb'

    def test_extract_css_utf8(self):
        result, css = extract_css(
            "<html><body>ä</body></html>", 'sample.html')
        assert css is None
        assert result == '<html>\n <body>\n  ä\n </body>\n</html>'

    def test_extract_css_utf8_unicode(self):
        result, css = extract_css(
            u"<html><body>ä</body></html>", 'sample.html')
        assert css is None
        assert result == '<html>\n <body>\n  ä\n </body>\n</html>'
        return

    def test_extract_css_complex_html(self):
        # Make sure we have styles purged and replaced by a link
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample2.html')
        html_input = open(html_input_path, 'rb').read()
        result, css = extract_css(html_input, 'sample.html')
        assert '<style' not in result
        link = '<link rel="stylesheet" type="text/css" href="sample.css" />'
        assert link in result
        return

    def test_extract_css_complex_css(self):
        # Make sure we get proper external stylesheets.
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample2.html')
        html_input = open(html_input_path, 'rb').read()
        result, css = extract_css(html_input, 'sample.html')
        assert len(css) == 150
        assert css.startswith('@page { size: 21cm')
        return

    def test_extract_css_no_empty_comments(self):
        # Make sure there are no empty comments in CSS
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample2.html')
        html_input = open(html_input_path, 'rb').read()
        result, css = extract_css(html_input, 'sample.html')
        assert '/*' not in result
        return

    def test_cleanup_html_fix_head_nums(self):
        html_input = '<body><h1>1.1Heading</h1></body>'
        result = cleanup_html(html_input)
        expected = '<body><h1><span class="u-o-headnum">%s</span>'
        expected += 'Heading</h1></body>'
        assert result == expected % ('1.1')

    def test_cleanup_html_fix_head_nums_no_nums(self):
        html_input = '<body><h1>Heading</h1></body>'
        result = cleanup_html(html_input)
        assert result == '<body><h1>Heading</h1></body>'

    def test_cleanup_html_fix_head_nums_trailing_dot(self):
        html_input = '<body><h1>1.1.Heading</h1></body>'
        result = cleanup_html(html_input)
        expected = '<body><h1><span class="u-o-headnum">%s</span>'
        expected += 'Heading</h1></body>'
        assert result == expected % ('1.1.')

    def test_cleanup_html_fix_head_nums_h6(self):
        html_input = '<body><h6>1.1.Heading</h6></body>'
        result = cleanup_html(html_input)
        expected = '<body><h6><span class="u-o-headnum">%s</span>'
        expected += 'Heading</h6></body>'
        assert result == expected % ('1.1.')

    def test_cleanup_html_fix_head_nums_tag_attrs(self):
        html_input = '<body><h6 class="foo">1.1.Heading</h6></body>'
        result = cleanup_html(html_input)
        expected = '<body><h6 class="foo"><span class="u-o-headnum">%s'
        expected += '</span>Heading</h6></body>'
        assert result == expected % ('1.1.')

    def test_cleanup_html_fix_head_nums_linebreaks(self):
        html_input = '<body><h1>\n 1.1.Heading</h1></body>'
        result = cleanup_html(html_input)
        expected = '<body><h1>\n <span class="u-o-headnum">%s</span>'
        expected += 'Heading</h1></body>'
        assert result == expected % ('1.1.')
