import sys
import os
import time
import subprocess
import urllib.request
import json
import asyncio
import websockets

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
url = "http://localhost:3000/"

async def debug_chrome_console():
    print("Launching Chrome in debugging mode...")
    chrome_proc = subprocess.Popen([
        chrome_path,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--no-sandbox",
        "--disable-gpu",
        "about:blank"
    ])
    
    time.sleep(3.0)
    
    try:
        # Get target websocket URL
        with urllib.request.urlopen("http://localhost:9222/json") as response:
            targets = json.loads(response.read().decode())
            # Find the target with type "page"
            page_target = next(t for t in targets if t["type"] == "page")
            ws_url = page_target["webSocketDebuggerUrl"]
            
        print(f"Connecting to Chrome WebSocket: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            # 1. Enable Log, Runtime, Page domains
            await websocket.send(json.dumps({"id": 1, "method": "Log.enable"}))
            await websocket.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
            await websocket.send(json.dumps({"id": 3, "method": "Page.enable"}))
            
            # 2. Navigate to URL
            print(f"Navigating to {url}...")
            await websocket.send(json.dumps({
                "id": 4,
                "method": "Page.navigate",
                "params": {"url": url}
            }))
            
            # 3. Read events for 5 seconds
            start_time = time.time()
            while time.time() - start_time < 5.0:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    data = json.loads(message)
                    
                    # Log console messages
                    if "method" in data:
                        method = data["method"]
                        params = data.get("params", {})
                        
                        if method == "Runtime.consoleAPICalled":
                            args = params.get("args", [])
                            values = [str(arg.get("value", "")) for arg in args]
                            print(f"[CONSOLE {params.get('type')}] {' '.join(values)}")
                            
                        elif method == "Runtime.exceptionThrown":
                            details = params.get("exceptionDetails", {})
                            exception = details.get("exception", {})
                            print(f"[JS EXCEPTION] {details.get('text')}: {exception.get('description')}")
                            
                        elif method == "Log.entryAdded":
                            entry = params.get("entry", {})
                            print(f"[LOG {entry.get('level')}] {entry.get('text')}")
                except asyncio.TimeoutError:
                    pass
                    
    except Exception as e:
        print(f"Error during debugging: {e}")
    finally:
        print("Terminating Chrome...")
        chrome_proc.terminate()

if __name__ == "__main__":
    asyncio.run(debug_chrome_console())
