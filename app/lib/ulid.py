"""
ULID (Universally Unique Lexicographically Sortable Identifier) helper.
Used as primary key for all models — sortable, URL-safe, 26 chars.
"""

import ulid as _ulid


def new_ulid() -> str:
    return str(_ulid.new())
