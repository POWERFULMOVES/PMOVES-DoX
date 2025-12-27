import asyncio
import json
import random
import time
import os
from nats.aio.client import Client as NATS

# Path to the demo data file
DEMO_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "demo", "collectionsHost.JSON")

def load_demo_data():
    """
    Load Postman collection demo data from JSON file.

    Returns:
        list: List containing collection data dict, or empty list if file not found.
    """
    try:
        with open(DEMO_DATA_PATH, 'r') as f:
            data = json.load(f)
            return [data]
    except FileNotFoundError:
        print(f"Warning: Demo file not found at {DEMO_DATA_PATH}. Using fallback.")
        return []

async def main():
    """
    Publish geometry events to NATS for visualization demo.

    Connects to NATS (localhost:4223) and continuously publishes:
    - Manifold updates (hyperbolic surface parameters)
    - Constellation updates (API endpoint/model points from demo collection)

    Publishes every 3 seconds to geometry.event.manifold and geometry.event.constellation.
    """
    nc = NATS()
    try:
        await nc.connect("nats://localhost:4223")
        print("Connected to NATS")

        demo_snapshots = load_demo_data()
        
        while True:
            snapshot = demo_snapshots[0] if demo_snapshots else {}
            
            t = time.time()
            
            manifold_payload = {
                "type": "manifold_update",
                "timestamp": t,
                "parameters": {
                    "uMin": 0, "uMax": 1,
                    "vMin": 0, "vMax": 1,
                    "t": t % 100,
                    "k": -0.5 + (0.1 * random.random()), # Hyperbolic baseline
                    "epsilon": 0.2
                }
            }
            
            # 2. Transform into Constellation (Tree)
            points = []
            
            # Extract Paths (Endpoints) - LIMIT to 10
            if "paths" in snapshot:
                for i, (path, methods) in enumerate(snapshot["paths"].items()):
                    if i >= 10: break
                    points.append({
                        "id": f"path_{path}",
                        "x": random.uniform(-15, 15),
                        "y": random.uniform(-15, 15),
                        "z": random.uniform(-5, 5),
                        "conf": 0.9,
                        "text": path,
                        "type": "endpoint"
                    })
            
            # Extract Definitions (Models) - LIMIT to 10
            if "definitions" in snapshot:
                for i, (def_name, def_body) in enumerate(snapshot["definitions"].items()):
                    if i >= 10: break
                    points.append({
                        "id": f"def_{def_name}",
                        "x": random.uniform(-20, 20),
                        "y": random.uniform(-20, 20),
                        "z": random.uniform(-10, 10),
                        "conf": 0.6,
                        "text": def_name,
                        "type": "model"
                    })

            # Fallback if empty
            if not points:
                 points = [
                     {"id": "p1", "x": -10, "y": 5, "conf": 0.9, "text": "No Data Found"},
                 ]

            # Create Super Nodes (Clusters)
            points_payload = {
                "type": "constellation_update",
                "super_nodes": [
                    {
                        "id": "root",
                        "label": "API Manifold",
                        "x": 0, "y": 0, "r": 30,
                        "constellations": [
                            {
                                "id": "swagger_constellation",
                                "spectrum": [0.5, 0.8, 0.9], # Blue-ish
                                "points": points
                            }
                        ]
                    }
                ]
            }

            await nc.publish("geometry.event.manifold", json.dumps(manifold_payload).encode())
            await nc.publish("geometry.event.constellation", json.dumps(points_payload).encode())
            
            print(f"Published demo update from {os.path.basename(DEMO_DATA_PATH)}")
            await asyncio.sleep(3)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
