"""Harness store. MongoDB when MONGODB_URI is set, otherwise a local JSON fallback
in .localdb/ so the loop can run before the Atlas cluster exists.

Collections: harness_versions, eval_runs, bookings, test_cases, flags.
"""

import json
import threading
from datetime import datetime, timezone

from .config import MONGODB_DB, MONGODB_URI, ROOT

COLLECTIONS = ["harness_versions", "eval_runs", "bookings", "test_cases", "flags"]


def now():
    return datetime.now(timezone.utc)


class _LocalCollection:
    """Just enough of the pymongo Collection API for this project."""

    _lock = threading.Lock()

    def __init__(self, path):
        self.path = path

    def _load(self):
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, docs):
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(docs, indent=2, default=str), encoding="utf-8")

    @staticmethod
    def _match(doc, query):
        return all(doc.get(k) == v for k, v in (query or {}).items())

    def insert_one(self, doc):
        with self._lock:
            docs = self._load()
            docs.append(doc)
            self._save(docs)

    def insert_many(self, new_docs):
        with self._lock:
            docs = self._load()
            docs.extend(new_docs)
            self._save(docs)

    def delete_many(self, query):
        with self._lock:
            self._save([d for d in self._load() if not self._match(d, query)])

    def update_many(self, query, update):
        with self._lock:
            docs = self._load()
            for d in docs:
                if self._match(d, query):
                    d.update(update.get("$set", {}))
            self._save(docs)

    def find(self, query=None, sort=None):
        docs = [d for d in self._load() if self._match(d, query)]
        for key, direction in reversed(sort or []):
            docs.sort(key=lambda d: d.get(key) or 0, reverse=direction < 0)
        return docs

    def find_one(self, query=None, sort=None):
        docs = self.find(query, sort)
        return docs[0] if docs else None

    def count_documents(self, query):
        return len(self.find(query))


class Store:
    def __init__(self):
        if MONGODB_URI:
            from pymongo import MongoClient

            self.backend = "mongodb"
            self.db = MongoClient(MONGODB_URI)[MONGODB_DB]
        else:
            self.backend = "local"
            self.db = {c: _LocalCollection(ROOT / ".localdb" / f"{c}.json") for c in COLLECTIONS}

    def col(self, name):
        return self.db[name]

    @staticmethod
    def _clean(doc):
        if doc:
            doc.pop("_id", None)
        return doc

    def _find(self, name, query=None, sort=None):
        if self.backend == "mongodb":
            cur = self.db[name].find(query or {})
            if sort:
                cur = cur.sort(sort)
            return [self._clean(d) for d in cur]
        return self.db[name].find(query, sort)

    # harness versions
    def save_harness(self, harness: dict):
        self.col("harness_versions").insert_one({**harness, "created_at": now()})

    def get_harness(self, version: int):
        return self._clean(self.col("harness_versions").find_one({"version": version}))

    def list_harnesses(self):
        return self._find("harness_versions", sort=[("version", 1)])

    def next_version(self):
        versions = self.list_harnesses()
        return max((h["version"] for h in versions), default=0) + 1

    def active_harness(self):
        """The harness the live app uses: the one marked active, else the newest."""
        hs = self.list_harnesses()
        active = [h for h in hs if h.get("active")]
        return (active or hs or [None])[-1]

    def set_active(self, version: int):
        col = self.col("harness_versions")
        col.update_many({}, {"$set": {"active": False}})
        col.update_many({"version": version}, {"$set": {"active": True}})

    # eval runs
    def save_eval(self, run: dict):
        self.col("eval_runs").insert_one({**run, "created_at": now()})

    def list_evals(self):
        return self._find("eval_runs", sort=[("harness_version", 1)])

    # bookings + flags
    def save_booking(self, booking: dict):
        self.col("bookings").insert_one({**booking, "created_at": now()})

    def save_flag(self, flag: dict):
        self.col("flags").insert_one({**flag, "created_at": now()})

    # test cases
    def load_test_cases(self):
        return self._find("test_cases", sort=[("id", 1)])

    def replace_test_cases(self, cases):
        col = self.col("test_cases")
        col.delete_many({})
        col.insert_many([dict(c) for c in cases])

    def reset(self):
        for c in COLLECTIONS:
            self.col(c).delete_many({})
