"""Copy every Hug Guardian collection from one MongoDB cluster to another. No model calls.

    python scripts/copy_db.py "mongodb+srv://OLD..." "mongodb+srv://NEW..."

Collections in the target are replaced, not merged.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymongo import MongoClient  # noqa: E402

from hug_guardian.config import MONGODB_DB  # noqa: E402
from hug_guardian.store import COLLECTIONS  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src = MongoClient(sys.argv[1], serverSelectionTimeoutMS=15000)[MONGODB_DB]
    dst = MongoClient(sys.argv[2], serverSelectionTimeoutMS=15000)[MONGODB_DB]
    for name in COLLECTIONS:
        docs = list(src[name].find())
        dst[name].delete_many({})
        if docs:
            dst[name].insert_many(docs)
        print(f"{name}: {len(docs)} copied")
