import asyncio
import ngrok
import click
import json
import os
from typing import List, Dict
from fastapi import FastAPI, HTTPException

app = FastAPI()
config_file = "ngrok_config.json"


class TunnelManager:
    def __init__(self):
        self.session = None
        self.tunnels = {}

    async def initialize_session(self):
        if self.session is None:
            self.session = await ngrok.SessionBuilder().authtoken_from_env().connect()
        return self.session

    async def create_tunnel(self, protocol: str, forwards_to: str) -> str:
        session = await self.initialize_session()
        listener = await session.http_endpoint().listen()
        listener.forward(forwards_to)
        url = listener.url()
        self.tunnels[url] = {"protocol": protocol, "forwards_to": forwards_to}
        self.save_tunnels()
        return url

    def delete_tunnel(self, url: str):
        if url in self.tunnels:
            del self.tunnels[url]
            self.save_tunnels()
        else:
            raise HTTPException(status_code=404, detail="Tunnel not found")

    def list_tunnels(self) -> List[Dict[str, str]]:
        return [{"url": url, **details} for url, details in self.tunnels.items()]

    def save_tunnels(self):
        with open(config_file, 'w') as file:
            json.dump(self.tunnels, file)

    def load_tunnels(self):
        if os.path.exists(config_file):
            with open(config_file, 'r') as file:
                self.tunnels = json.load(file)


tunnel_manager = TunnelManager()
tunnel_manager.load_tunnels()


@app.get("/tunnels", response_model=List[Dict[str, str]])
def list_tunnels():
    return tunnel_manager.list_tunnels()


@app.post("/tunnels")
async def create_tunnel(tunnel: Dict[str, str]):
    protocol = tunnel.get("protocol", "http")
    forwards_to = tunnel["forwards_to"]
    url = await tunnel_manager.create_tunnel(protocol, forwards_to)
    return {"url": url, "protocol": protocol, "forwards_to": forwards_to}


@app.delete("/tunnels/{url}")
def delete_tunnel(url: str):
    tunnel_manager.delete_tunnel(url)
    return {"detail": "Tunnel deleted"}


async def setup_listener():
    listen = "localhost:8000"
    session = await ngrok.SessionBuilder().authtoken_from_env().connect()
    listener = await (
        session.http_endpoint()
        .listen()
    )
    url = listener.url()
    click.secho(
        f"API is exposed at: {url}",
        fg="green",
        bold=True,
    )
    listener.forward(listen)
    return url


async def run_ngrok_listener():
    try:
        # Check if asyncio loop is already running. If so, piggyback on it to run the ngrok listener.
        running_loop = asyncio.get_running_loop()
        url = await running_loop.create_task(setup_listener())
    except RuntimeError:
        # No existing loop is running, so we can run the ngrok listener on a new loop.
        url = await asyncio.run(setup_listener())
    return url


if __name__ == "__main__":
    import uvicorn
    url = asyncio.run(run_ngrok_listener())
    print(f"Ngrok tunnel URL: {url}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
