import asyncio
import json
import os
import nats
from nats.errors import ConnectionClosedError, TimeoutError, NoRespondersError
from nats.js.api import StreamConfig

# Default to "nats" hostname for Docker, or can be overridden
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")

async def main():
    print(f"Connecting to NATS at {NATS_URL}...")
    try:
        nc = await nats.connect(NATS_URL)
        print("Connected to NATS!")

        # Create JetStream context
        js = nc.jetstream()
        print("JetStream context created.")

        # Check for GEOMETRY stream
        try:
            stream_info = await js.stream_info("GEOMETRY")
            print(f"Stream GEOMETRY found: {stream_info.config.subjects}")
            # simple check: if subjects are missing, delete and recreate
            if "tokenism.cgp.>" not in stream_info.config.subjects:
                 print("Stream configuration mismatch. Deleting and recreating...")
                 await js.delete_stream("GEOMETRY")
                 raise Exception("Stream deleted for update")
        except Exception:
            print(f"Creating GEOMETRY stream with correct namespaces...")
            await js.add_stream(name="GEOMETRY", subjects=["geometry.event.>", "tokenism.cgp.>"])
            print("Stream GEOMETRY created.")

        # Publish test messages to known namespaces
        await js.publish("geometry.event.test", json.dumps({"test": "data"}).encode())
        print("Published test message to geometry.event.test")
        
        await js.publish("tokenism.cgp.test", json.dumps({"test": "data"}).encode())
        print("Published test message to tokenism.cgp.test")

        await nc.close()
        print("Connection closed.")

    except Exception as e:
        print(f"NATS Verification Failed: {e}")

if __name__ == '__main__':
    asyncio.run(main())
