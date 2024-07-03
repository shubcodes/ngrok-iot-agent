import asyncio
import ngrok
import click
import json
import os
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

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

    async def create_tunnel(self, protocol: str, forwards_to: str, domain: str = None) -> str:
        session = await self.initialize_session()
        listener = session.http_endpoint()
        if domain:
            listener = listener.domain(domain)
        listener = await listener.listen()
        listener.forward(forwards_to)
        url = listener.url()
        self.tunnels[url] = {"protocol": protocol, "forwards_to": forwards_to, "domain": domain}
        self.save_tunnels()
        return url

    async def recreate_tunnel(self, url: str, protocol: str, forwards_to: str, domain: str = None):
        session = await self.initialize_session()
        listener = session.http_endpoint()
        if domain:
            listener = listener.domain(domain)
        listener = await listener.listen()
        listener.forward(forwards_to)
        if listener.url() != url:
            # If the URL does not match, we need to update the stored URL
            del self.tunnels[url]
            self.tunnels[listener.url()] = {"protocol": protocol, "forwards_to": forwards_to, "domain": domain}
            self.save_tunnels()
        else:
            self.tunnels[url] = {"protocol": protocol, "forwards_to": forwards_to, "domain": domain}

    def delete_tunnel(self, url_part: str):
        # Find the full URL matching the provided part
        full_url = next((url for url in self.tunnels if url_part in url), None)
        if full_url:
            del self.tunnels[full_url]
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
    domain = tunnel.get("domain")
    url = await tunnel_manager.create_tunnel(protocol, forwards_to, domain)
    return {"url": url, "protocol": protocol, "forwards_to": forwards_to, "domain": domain}


@app.delete("/tunnels/{url_part}")
def delete_tunnel(url_part: str):
    tunnel_manager.delete_tunnel(url_part)
    return JSONResponse(content={"detail": "Tunnel deleted"}, status_code=200)


async def setup_listener():
    listen = "localhost:8000"
    domain = "shub-reserved.ngrok.io"  # Replace with your reserved domain ****IMPORTANT****
    session = await ngrok.SessionBuilder().authtoken_from_env().connect()
    listener = await session.http_endpoint().domain(domain).listen()
    url = listener.url()
    click.secho(
        f"API is exposed at: {url}",
        fg="green",
        bold=True,
    )
    listener.forward(listen)
    return url


async def recreate_saved_tunnels():
    new_tunnels = {}
    for url, details in list(tunnel_manager.tunnels.items()):
        domain = details.get("domain")
        session = await tunnel_manager.initialize_session()
        listener = session.http_endpoint()
        if domain:
            listener = listener.domain(domain)
        listener = await listener.listen()
        listener.forward(details["forwards_to"])
        new_url = listener.url()
        new_tunnels[new_url] = details
        if new_url != url:
            del tunnel_manager.tunnels[url]
    tunnel_manager.tunnels.update(new_tunnels)
    tunnel_manager.save_tunnels()


async def run_ngrok_listener():
    try:
        # Check if asyncio loop is already running. If so, piggyback on it to run the ngrok listener.
        running_loop = asyncio.get_running_loop()
        url = await setup_listener()
        await recreate_saved_tunnels()
    except RuntimeError:
        # No existing loop is running, so we can run the ngrok listener on a new loop.
        url = await asyncio.run(setup_listener())
        await asyncio.run(recreate_saved_tunnels())
    return url


if __name__ == "__main__":
    import uvicorn
    url = asyncio.run(run_ngrok_listener())
    print(f"Ngrok tunnel URL: {url}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
