import asyncio

import websockets


async def test_conn(origin):
    uri = "ws://localhost:8000/api/ws"
    try:
        async with websockets.connect(uri, origin=origin) as websocket:
            print(f"Success with Origin: {origin}")
    except Exception as e:
        print(f"Failed with Origin: {origin} -> {e}")


async def main():
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        None,
    ]
    for orig in origins:
        await test_conn(orig)


if __name__ == "__main__":
    asyncio.run(main())
