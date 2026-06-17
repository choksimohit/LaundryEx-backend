import asyncio
import json
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

BACKUP_FILE = ROOT_DIR / 'laundry-express-backup-2026-06-04.json'

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

SKIP_COLLECTIONS = {'_meta'}

async def restore():
    print(f"Connecting to database: {os.environ['DB_NAME']}")

    with open(BACKUP_FILE) as f:
        data = json.load(f)

    for collection_name, documents in data.items():
        if collection_name in SKIP_COLLECTIONS:
            print(f"Skipping {collection_name}")
            continue
        if not documents:
            print(f"Skipping {collection_name} (empty)")
            continue

        collection = db[collection_name]
        await collection.delete_many({})
        await collection.insert_many(documents)
        print(f"Restored {len(documents)} documents into '{collection_name}'")

    print("\nRestore complete!")

if __name__ == "__main__":
    asyncio.run(restore())
    client.close()
