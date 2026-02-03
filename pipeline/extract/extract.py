import asyncio
import websockets

async def get_one_message():
    uri = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"
    async with websockets.connect(uri) as websocket:
        message = await websocket.recv()
        print(message)

if __name__ == "__main__":
    asyncio.run(get_one_message())
