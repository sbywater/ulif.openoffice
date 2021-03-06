import filecmp
import os
import pytest
import shutil
try:
    from cStringIO import StringIO  # Python 2.x
except ImportError:                 # pragma: no cover
    from io import StringIO         # Python 3.x
from ulif.openoffice.cachemanager import Bucket, CacheManager, get_marker


@pytest.fixture(scope="function")
def cache_env(request, tmpdir):
    (tmpdir / "src1.txt").write("source1\n", ensure=True)
    (tmpdir / "src2.txt").write("source2\n")
    (tmpdir / "result1.txt").write("result1\n")
    (tmpdir / "result2.txt").write("result2\n")
    (tmpdir / "result3.txt").write("result3\n")
    (tmpdir / "result4.txt").write("result4\n")
    return tmpdir


class TestHelpers(object):

    def test_get_marker(self):
        # Make sure, sorted dicts get the same marker
        result1 = get_marker()
        result2 = get_marker(options={})
        result3 = get_marker(options={'b': '0', 'a': '1'})
        result4 = get_marker(options={'a': '1', 'b': '0'})
        assert result1 == 'W10'
        assert result2 == 'W10'
        assert result3 == result4
        assert result2 != result3


class TestCacheBucket(object):
    # Tests for CacheBucket

    def test_init_creates_subdirs(self, tmpdir):
        # a new bucket contains certain subdirs and a file
        Bucket(str(tmpdir))
        for filename in ['sources', 'repr', 'keys', 'data']:
            assert tmpdir.join(filename).exists()

    def test_init_sets_attributes(self, tmpdir):
        # Main attributes are set properly...
        bucket = Bucket(str(tmpdir))
        assert bucket.srcdir == tmpdir / "sources"
        assert bucket.resultdir == tmpdir / "repr"
        assert bucket.keysdir == tmpdir / "keys"
        assert bucket._data == dict(
            version=1, curr_src_num=0, curr_repr_num=dict())

    def test_init_internal_data(self, tmpdir):
        # A bucket with same path won't overwrite existing data...
        bucket1 = Bucket(str(tmpdir))
        assert bucket1._get_internal_data() == dict(
            version=1, curr_src_num=0, curr_repr_num={})
        to_set = dict(version=1, curr_src_num=1, curr_repr_num={'1': 2})
        bucket1._set_internal_data(to_set)
        assert bucket1._get_internal_data() == to_set
        bucket2 = Bucket(str(tmpdir))
        assert bucket2._get_internal_data() == to_set

    def test_curr_src_num(self, tmpdir):
        # we can get/set current source number
        bucket = Bucket(str(tmpdir))
        assert bucket.get_current_source_num() == 0
        bucket.set_current_source_num(12)
        assert bucket.get_current_source_num() == 12

    def test_curr_repr_num(self, tmpdir):
        # we can get/set current representation number
        bucket = Bucket(str(tmpdir))
        assert bucket.get_current_repr_num(1) == 0
        assert bucket.get_current_repr_num('2') == 0
        bucket.set_current_repr_num('1', 12)
        assert bucket.get_current_repr_num('1') == 12
        assert bucket.get_current_repr_num('2') == 0

    def test_get_stored_source_num(self, cache_env):
        # we can test whether a source file is stored in a bucket already.
        bucket = Bucket(str(cache_env.join("cache")))
        src1 = cache_env / "src1.txt"
        src2 = cache_env / "src2.txt"
        assert bucket.get_stored_source_num(str(src1)) is None
        assert bucket.get_stored_source_num(str(src2)) is None
        shutil.copyfile(str(src1), os.path.join(bucket.srcdir, "source_1"))
        assert bucket.get_stored_source_num(str(src1)) == 1
        assert bucket.get_stored_source_num(str(src2)) is None
        shutil.copyfile(str(src2), os.path.join(bucket.srcdir, "source_2"))
        assert bucket.get_stored_source_num(str(src1)) == 1
        assert bucket.get_stored_source_num(str(src2)) == 2

    def test_get_stored_repr_num(self, tmpdir):
        # we can get a representation number if the repective key is
        # stored in the bucket already.
        bucket = Bucket(str(tmpdir.join("cache")))
        key_path1 = tmpdir / "cache" / "keys" / "1" / "1.key"
        key_path2 = tmpdir / "cache" / "keys" / "1" / "2.key"
        key_path3 = tmpdir / "cache" / "keys" / "2" / "1.key"
        assert bucket.get_stored_repr_num(1, 'somekey') is None
        assert bucket.get_stored_repr_num(1, 'otherkey') is None
        assert bucket.get_stored_repr_num(2, 'somekey') is None
        assert bucket.get_stored_repr_num(2, 'otherkey') is None
        key_path1.write('otherkey', ensure=True)
        assert bucket.get_stored_repr_num(1, 'somekey') is None
        assert bucket.get_stored_repr_num(1, 'otherkey') == 1
        assert bucket.get_stored_repr_num(2, 'somekey') is None
        assert bucket.get_stored_repr_num(2, 'otherkey') is None
        key_path2.write('somekey', ensure=True)
        assert bucket.get_stored_repr_num(1, 'somekey') == 2
        assert bucket.get_stored_repr_num(1, 'otherkey') == 1
        assert bucket.get_stored_repr_num(2, 'somekey') is None
        assert bucket.get_stored_repr_num(2, 'otherkey') is None
        key_path3.write('somekey', ensure=True)
        assert bucket.get_stored_repr_num(1, 'somekey') == 2
        assert bucket.get_stored_repr_num(1, 'otherkey') == 1
        assert bucket.get_stored_repr_num(2, 'somekey') == 1
        assert bucket.get_stored_repr_num(2, 'otherkey') is None

    def test_store_representation_no_key(self, cache_env):
        # we can store sources with their representations
        bucket = Bucket(str(cache_env.join("cache")))
        res = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"))
        source_path = cache_env / "cache" / "sources" / "source_1"
        result_path = cache_env / "cache" / "repr" / "1" / "1" / "result1.txt"
        assert res == "1_1"
        assert source_path.isfile()
        assert source_path.read() == "source1\n"
        assert result_path.dirpath().isdir()
        assert result_path.isfile()
        assert result_path.read() == "result1\n"
        assert (cache_env / "cache" / "keys" / "1" / "1.key").isfile()
        assert (cache_env / "cache" / "keys" / "1" / "1.key").read() == ""

    def test_store_representation_string_key(self, cache_env):
        #  we can store sources with their representations and a string key
        bucket = Bucket(str(cache_env.join("cache")))
        res = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"), repr_key="somekey")
        assert res == "1_1"
        assert (
            cache_env / "cache" / "keys" / "1" / "1.key").read() == 'somekey'

    def test_store_representation_file_key(self, cache_env):
        #  we can store sources with their representations and a key
        #  stored in a file.
        bucket = Bucket(str(cache_env.join("cache")))
        res = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"),
            repr_key=StringIO("somekey"))
        assert res == "1_1"
        assert (
            cache_env / "cache" / "keys" / "1" / "1.key").read() == 'somekey'

    def test_store_representation_update_result(self, cache_env):
        # if we send a different representation for the same source
        # and key, the old representation will be replaced.
        bucket = Bucket(str(cache_env / "cache"))
        res1 = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"), repr_key='mykey')
        res2 = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result2.txt"), repr_key='mykey')
        assert res1 == "1_1"
        assert res2 == "1_1"
        result_dir = cache_env / "cache" / "repr" / "1" / "1"
        assert result_dir.join("result1.txt").exists() is False
        assert result_dir.join("result2.txt").exists() is True
        assert result_dir.join("result2.txt").read() == "result2\n"

    def test_get_representation_unstored(self, tmpdir):
        # we cannot get unstored representations
        bucket = Bucket(str(tmpdir.join("cache")))
        assert bucket.get_representation("1_1") is None

    def test_get_representation_stored(self, cache_env):
        # we can get paths of representations
        bucket = Bucket(str(cache_env.join("cache")))
        res1 = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"), repr_key=b'mykey')
        res2 = bucket.get_representation(res1)
        assert res1 == "1_1"
        assert res2 == cache_env / "cache" / "repr" / "1" / "1" / "result1.txt"

    def test_keys(self, cache_env):
        # we can get a list of all bucket keys in a bucket.
        bucket = Bucket(str(cache_env))
        assert list(bucket.keys()) == []
        key1 = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"), repr_key='foo')
        assert list(bucket.keys()) == [key1, ]
        key2 = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result2.txt"), repr_key='bar')
        assert sorted(list(bucket.keys())) == [key1, key2]
        key3 = bucket.store_representation(
            str(cache_env / "src1.txt"),
            str(cache_env / "result3.txt"), repr_key='baz')
        assert sorted(list(bucket.keys())) == [key1, key2, key3]


class TestCacheManager(object):
    # Tests for class `CacheManager`

    def test_markerhandling(self, tmpdir):
        # we can dissolve markers from cache_keys.
        cm = CacheManager(str(tmpdir))
        marker_string = cm._compose_cache_key('somefakedhash', 3)
        assert marker_string == "somefakedhash_3"
        hash_val, bucket_marker = cm._dissolve_cache_key("somefakedhash_3")
        assert hash_val == "somefakedhash"
        assert bucket_marker == "3"
        assert cm._dissolve_cache_key("asd") == (None, None)
        assert cm._dissolve_cache_key(None) == (None, None)

    def test_init(self, tmpdir):
        # we can initialize a cache manager with default depth
        cm = CacheManager(str(tmpdir.join("cache")))
        assert cm.level == 1
        assert cm.cache_dir == tmpdir.join("cache")

    def test_init_level(self, tmpdir):
        # we can set a level (depth) when creating cache managers
        cm = CacheManager(str(tmpdir.join("cache")), level=3)
        assert cm.level == 3

    def test_init_creates_dir(self, tmpdir):
        # a cache dir is created if neccessary
        cache_dir = tmpdir / "cache"
        assert cache_dir.exists() is False
        CacheManager(str(cache_dir))
        assert cache_dir.isdir() is True

    def test_init_fails_loudly(self, tmpdir):
        # If we get a file as cache dir (instead of a directory), we
        # fail loudly...
        a_file = tmpdir.join("some_file.txt")
        a_file.write("this-is-not-a-dir")
        with pytest.raises(IOError):
            CacheManager(str(a_file))

    def test_compose_marker(self, tmpdir):
        # we can compose cache keys
        cm = CacheManager(str(tmpdir))
        marker2 = cm._compose_cache_key('some_hash_digest', 'bucket_marker')
        assert marker2 == 'some_hash_digest_bucket_marker'

    def test_get_bucket_path(self, tmpdir):
        # we can get a bucket path from a hash value
        cm = CacheManager(str(tmpdir.join("cache")))
        tmpdir.join("src.txt").write("source1\n")
        hash_val = cm.get_hash(str(tmpdir / "src.txt"))
        assert cm._get_bucket_path(hash_val) == (
            tmpdir / "cache" / "73" / "737b337e605199de28b3b64c674f9422")

    def test_prepare_cache_dir(self, tmpdir):
        # _prepare_cache_dir creates a cache dir normally
        cm = CacheManager(str(tmpdir.join("cache")))
        new_dir = tmpdir.join("new_dir")
        cm.cache_dir = str(new_dir)
        cm._prepare_cache_dir()
        assert new_dir.isdir() is True

    def test_prepare_cache_dir_none(self, tmpdir):
        # we can create a cache manager without any cache dir
        cm = CacheManager(str(tmpdir))
        cm.cache_dir = None
        cm._prepare_cache_dir()
        assert cm.cache_dir is None

    def test_prepare_cache_dir_broken(self, tmpdir):
        # we fail loudly if we cannot create a cache dir
        cm = CacheManager(str(tmpdir))
        tmpdir.join("not-a-dir.txt").write("foo")     # broken dir
        cm.cache_dir = str(tmpdir / "not-a-dir.txt")
        with pytest.raises(IOError):
            cm._prepare_cache_dir()

    def test_get_cached_file_empty(self, cache_env):
        # while cache is empty we get `None` when asking for cached files.
        cm = CacheManager(str(cache_env / "cache"))
        path = cm.get_cached_file(str(cache_env / "src1.txt"))
        assert path is None

    def test_get_cached_file(self, cache_env):
        # we can get a file cached before.
        cm = CacheManager(str(cache_env / "cache"))
        cache_key = cm.register_doc(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"))
        path = cm.get_cached_file(cache_key)
        assert path is not None
        assert open(path, 'r').read() == (
            cache_env / "result1.txt").read()

    def test_get_cached_file_w_key(self, cache_env):
        # we can get a cached file, stored under a key
        cm = CacheManager(str(cache_env / "cache"))
        cache_key = cm.register_doc(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"),
            repr_key='foo')
        path = cm.get_cached_file(cache_key)
        assert path is not None
        assert open(path, 'r').read() == (
            cache_env / "result1.txt").read()

    def test_get_cached_file_w_key_from_file(self, cache_env):
        # we can get a cached file, stored under a key, which is a file
        cm = CacheManager(str(cache_env / "cache"))
        cache_key = cm.register_doc(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"),
            repr_key=StringIO('foo'))
        path = cm.get_cached_file(cache_key)
        assert path is not None
        assert open(path, 'r').read() == (
            cache_env / "result1.txt").read()

    def test_get_cached_file_invalid_cache_key(self, tmpdir):
        # invalid/unused cache keys return `None` as cached file.
        cm = CacheManager(str(tmpdir))
        assert cm.get_cached_file("not-existing") is None

    def test_get_cached_file_by_src(self, cache_env):
        # we can get a cached file by source file and options
        cm = CacheManager(str(cache_env / "cache"))
        # without a cache key
        my_id = cm.register_doc(
            str(cache_env / "src1.txt"),
            str(cache_env / "result1.txt"))
        path, key = cm.get_cached_file_by_source(
            str(cache_env / "src1.txt"))
        assert open(path, "r").read() == (
            cache_env / "result1.txt").read()
        assert key == '737b337e605199de28b3b64c674f9422_1_1'
        assert my_id == key

    def test_get_cached_file_by_src_failed(self, cache_env):
        # uncached files result in `None` as result
        cm = CacheManager(str(cache_env))
        result, key = cm.get_cached_file_by_source(
            str(cache_env / "src1.txt"))
        assert result is None
        assert key is None

    def test_get_cached_file_by_src_w_key(self, cache_env):
        cm = CacheManager(str(cache_env / "cache"))
        src = cache_env / "src1.txt"
        result1 = cache_env / "result1.txt"
        result2 = cache_env / "result2.txt"
        my_id1 = cm.register_doc(str(src), str(result1), 'mykey')
        path1, key1 = cm.get_cached_file_by_source(str(src), 'mykey')
        assert filecmp.cmp(path1, str(result1), shallow=False)
        assert key1 == '737b337e605199de28b3b64c674f9422_1_1'
        assert key1 == my_id1
        # yet not existent cache file
        path2, key2 = cm.get_cached_file_by_source(str(src), 'otherkey')
        assert path2 is None
        assert key2 is None
        # store and retrieve 2nd cache file
        my_id3 = cm.register_doc(str(src), str(result2), 'otherkey')
        path3, key3 = cm.get_cached_file_by_source(str(src), 'otherkey')
        assert filecmp.cmp(path3, str(result2), shallow=False)
        assert key3 == '737b337e605199de28b3b64c674f9422_1_2'
        assert key3 == my_id3
        return

    def test_register_doc(self, cache_env):
        # we can register docs
        cm = CacheManager(str(cache_env / "cache"))
        src1 = str(cache_env / "src1.txt")
        src2 = str(cache_env / "src2.txt")
        result1 = str(cache_env / "result1.txt")
        result2 = str(cache_env / "result2.txt")
        marker1 = cm.register_doc(src1, result1)
        assert marker1 == '737b337e605199de28b3b64c674f9422_1_1'
        marker2 = cm.register_doc(src1, result1)
        assert marker2 == '737b337e605199de28b3b64c674f9422_1_1'
        marker3 = cm.register_doc(src1, result2, repr_key="foo")
        assert marker3 == '737b337e605199de28b3b64c674f9422_1_2'
        marker4 = cm.register_doc(src2, result2, repr_key="foo")
        assert marker4 == 'd5aa51d7fb180729089d2de904f7dffe_1_1'
        marker5 = cm.register_doc(src2, result2, repr_key=StringIO("bar"))
        assert marker5 == 'd5aa51d7fb180729089d2de904f7dffe_1_2'

    def test_get_hash(self, cache_env, samples_dir):
        # we can compute a hash for a source file.
        cm = CacheManager(str(cache_env))
        hash1 = cm.get_hash(str(cache_env / "src1.txt"))
        hash2 = cm.get_hash(str(cache_env / "src2.txt"))
        hash3 = cm.get_hash(str(samples_dir / "testdoc1.doc"))
        assert hash1 == '737b337e605199de28b3b64c674f9422'
        assert hash2 == 'd5aa51d7fb180729089d2de904f7dffe'
        assert hash3 == '443a07e0e92b7dc6b21f8be6a388f05f'
        with pytest.raises(TypeError):
            cm.get_hash()

    def test_keys(self, cache_env):
        # we can get all cache keys
        cm = CacheManager(str(cache_env / "cache"))
        src1 = str(cache_env / "src1.txt")
        src2 = str(cache_env / "src2.txt")
        result1 = str(cache_env / "result1.txt")
        result2 = str(cache_env / "result2.txt")
        key1 = cm.register_doc(src1, result1, 'foo')
        assert list(cm.keys()) == ['737b337e605199de28b3b64c674f9422_1_1']
        assert key1 == '737b337e605199de28b3b64c674f9422_1_1'
        key2 = cm.register_doc(src1, result2, 'bar')
        assert sorted(list(cm.keys())) == [
            '737b337e605199de28b3b64c674f9422_1_1',
            '737b337e605199de28b3b64c674f9422_1_2',
        ]
        assert key2 == '737b337e605199de28b3b64c674f9422_1_2'
        key3 = cm.register_doc(src2, result1, 'baz')
        assert sorted(list(cm.keys())) == [
            '737b337e605199de28b3b64c674f9422_1_1',
            '737b337e605199de28b3b64c674f9422_1_2',
            'd5aa51d7fb180729089d2de904f7dffe_1_1',
        ]
        assert key3 == 'd5aa51d7fb180729089d2de904f7dffe_1_1'

    def test_keys_custom_level(self, cache_env):
        # we can get all cache keys, even if a custom cache level is set
        # (and keys are stored in different location).
        cm = CacheManager(str(cache_env / "cache"), level=3)
        src1 = str(cache_env / "src1.txt")
        src2 = str(cache_env / "src2.txt")
        result1 = str(cache_env / "result1.txt")
        result2 = str(cache_env / "result2.txt")
        key1 = cm.register_doc(src1, result1, 'foo')
        assert list(cm.keys()) == ['737b337e605199de28b3b64c674f9422_1_1']
        assert key1 == '737b337e605199de28b3b64c674f9422_1_1'
        key2 = cm.register_doc(src1, result2, 'bar')
        assert sorted(list(cm.keys())) == [
            '737b337e605199de28b3b64c674f9422_1_1',
            '737b337e605199de28b3b64c674f9422_1_2',
        ]
        assert key2 == '737b337e605199de28b3b64c674f9422_1_2'
        key3 = cm.register_doc(src2, result1, 'baz')
        assert sorted(list(cm.keys())) == [
            '737b337e605199de28b3b64c674f9422_1_1',
            '737b337e605199de28b3b64c674f9422_1_2',
            'd5aa51d7fb180729089d2de904f7dffe_1_1',
        ]
        assert key3 == 'd5aa51d7fb180729089d2de904f7dffe_1_1'


class NotHashingCacheManager(CacheManager):
    # a cache manager that always returns the same hash
    def get_hash(self, path=None):
        return 'somefakedhash'


class TestCollision(object):
    # make sure hash collisions are handled correctly
    def test_collisions(self, cache_env):
        cm = NotHashingCacheManager(cache_dir=str(cache_env / "cache"))
        src1 = str(cache_env / "src1.txt")
        src2 = str(cache_env / "src2.txt")
        result1 = str(cache_env / "result1.txt")
        result2 = str(cache_env / "result2.txt")
        result3 = str(cache_env / "result3.txt")
        result4 = str(cache_env / "result4.txt")
        cm.register_doc(src1, result1, repr_key="pdf")
        cm.register_doc(src1, result2, repr_key="html")
        cm.register_doc(src2, result3, repr_key="pdf")
        cm.register_doc(src2, result4, repr_key="html")
        basket_path = cache_env / "cache" / "so" / "somefakedhash"
        assert (basket_path / "sources" / "source_1").isfile()
        assert (basket_path / "sources" / "source_2").isfile()
        repr_path = basket_path / "repr"
        assert (repr_path / "1" / "1" / "result1.txt").read() == ("result1\n")
        assert (repr_path / "1" / "2" / "result2.txt").read() == ("result2\n")
        assert (repr_path / "2" / "1" / "result3.txt").read() == ("result3\n")
        assert (repr_path / "2" / "2" / "result4.txt").read() == ("result4\n")
