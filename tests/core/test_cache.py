import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.cache import (
    CacheKeys,
    cache_delete,
    cache_get,
    cache_set,
    token_hash,
)


# ── token_hash ────────────────────────────────────────────────────────────────

def test_token_hash_is_24_chars():
    result = token_hash("some-jwt-token")
    assert len(result) == 24


def test_token_hash_is_deterministic():
    assert token_hash("abc") == token_hash("abc")


def test_token_hash_differs_for_different_tokens():
    assert token_hash("token-a") != token_hash("token-b")


def test_token_hash_does_not_contain_raw_token():
    t = "super-secret-jwt"
    assert t not in token_hash(t)


# ── CacheKeys ─────────────────────────────────────────────────────────────────

def test_cache_key_auth_user():
    assert CacheKeys.auth_user("abc123") == "au:abc123"


def test_cache_key_tenant_member():
    assert CacheKeys.tenant_member("tid1", "uid1") == "tm:tid1:uid1"


def test_cache_key_dashboard():
    assert CacheKeys.dashboard("tid1", "uid1") == "ds:tid1:uid1"


def test_cache_key_dashboard_period():
    key = CacheKeys.dashboard_period("tid1", "uid1", "2026-01-01", "2026-01-31")
    assert key == "ds:p:tid1:uid1:2026-01-01:2026-01-31"


def test_cache_key_projects_admin():
    assert CacheKeys.projects_admin("tid1") == "pj:tid1:all"


def test_cache_key_projects_member():
    assert CacheKeys.projects_member("tid1", "uid1") == "pj:tid1:uid1"


def test_cache_key_task_statuses():
    assert CacheKeys.task_statuses("pid1") == "ts:pid1"


def test_cache_key_tasks():
    assert CacheKeys.tasks("pid1") == "tk:pid1"


def test_cache_key_master_materials():
    assert CacheKeys.master_materials("tid1") == "mm:tid1"


def test_cache_key_labour_types():
    assert CacheKeys.labour_types("tid1") == "lt:tid1"


def test_cache_key_attendance():
    assert CacheKeys.attendance("pid1", "2026-03-17") == "att:pid1:2026-03-17"


def test_cache_key_expense():
    assert CacheKeys.expense("pid1") == "exp:pid1"


def test_cache_key_dr_recent_dates():
    assert CacheKeys.dr_recent_dates("pid1") == "dr:rd:pid1"


def test_cache_key_dr_list():
    assert CacheKeys.dr_list("pid1", "2026-03-17") == "dr:l:pid1:2026-03-17"


def test_cache_key_dr_entries_all():
    assert CacheKeys.dr_entries_all("pid1", "2026-03-17") == "dr:ea:pid1:2026-03-17"


def test_cache_key_dr_entries_member():
    key = CacheKeys.dr_entries_member("pid1", "uid1", "2026-03-17")
    assert key == "dr:em:pid1:uid1:2026-03-17"


# ── cache_get ─────────────────────────────────────────────────────────────────

def test_cache_get_returns_none_when_redis_is_none():
    assert cache_get(None, "any-key") is None


def test_cache_get_returns_none_on_cache_miss():
    redis = MagicMock()
    redis.get.return_value = None
    assert cache_get(redis, "missing-key") is None


def test_cache_get_returns_deserialised_dict():
    redis = MagicMock()
    redis.get.return_value = json.dumps({"foo": "bar"})
    result = cache_get(redis, "key")
    assert result == {"foo": "bar"}


def test_cache_get_returns_deserialised_list():
    redis = MagicMock()
    redis.get.return_value = json.dumps([1, 2, 3])
    result = cache_get(redis, "key")
    assert result == [1, 2, 3]


def test_cache_get_returns_none_on_redis_error():
    redis = MagicMock()
    redis.get.side_effect = Exception("connection refused")
    assert cache_get(redis, "key") is None  # must not raise


# ── cache_set ─────────────────────────────────────────────────────────────────

def test_cache_set_is_noop_when_redis_is_none():
    cache_set(None, "key", {"x": 1}, 60)  # must not raise


def test_cache_set_stores_json_with_ttl():
    redis = MagicMock()
    cache_set(redis, "key", {"x": 1}, 60)
    redis.set.assert_called_once_with("key", json.dumps({"x": 1}), ex=60)


def test_cache_set_is_noop_on_redis_error():
    redis = MagicMock()
    redis.set.side_effect = Exception("timeout")
    cache_set(redis, "key", {"x": 1}, 60)  # must not raise


# ── cache_delete ──────────────────────────────────────────────────────────────

def test_cache_delete_is_noop_when_redis_is_none():
    cache_delete(None, "key1", "key2")  # must not raise


def test_cache_delete_is_noop_when_no_keys():
    redis = MagicMock()
    cache_delete(redis)
    redis.delete.assert_not_called()


def test_cache_delete_single_key():
    redis = MagicMock()
    cache_delete(redis, "key1")
    redis.delete.assert_called_once_with("key1")


def test_cache_delete_multiple_keys_single_call():
    redis = MagicMock()
    cache_delete(redis, "key1", "key2", "key3")
    redis.delete.assert_called_once_with("key1", "key2", "key3")


def test_cache_delete_is_noop_on_redis_error():
    redis = MagicMock()
    redis.delete.side_effect = Exception("timeout")
    cache_delete(redis, "key1")  # must not raise
