import asyncio
import websockets
import json

async def main():
    uri = "ws://localhost:4455"
    async with websockets.connect(uri) as websocket:
        # Receive hello
        await websocket.recv()

        # Send identify (no auth)
        await websocket.send(json.dumps({
            "op": 1,
            "d": {
                "rpcVersion": 1
            }
        }))
        await websocket.recv()  # Identify response

        # Construct bounce_start message
        bounce_start_msg = {
            "op": 6,
            "d": {
                "requestType": "CallVendorRequest",
                "requestId": "bounce-start-1",
                "vendorName": "script",
                "requestData": {
                    "requestType": "bounce_start",
                    "source": "CG1 Group"
                }
            }
        }

        print("Sending bounce_start:")
        print(json.dumps(bounce_start_msg, indent=2))
        await websocket.send(json.dumps(bounce_start_msg))
        print(await websocket.recv())

        await asyncio.sleep(5)

        # Construct bounce_stop message
        bounce_stop_msg = {
            "op": 6,
            "d": {
                "requestType": "CallVendorRequest",
                "requestId": "bounce-stop-1",
                "vendorName": "script",
                "requestData": {
                    "requestType": "bounce_stop",
                    "source": "CG1 Group"
                }
            }
        }

        print("Sending bounce_stop:")
        print(json.dumps(bounce_stop_msg, indent=2))
        await websocket.send(json.dumps(bounce_stop_msg))
        print(await websocket.recv())

asyncio.run(main())
