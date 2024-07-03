#!/usr/bin/env python

import asyncio
import logging
import ngrok
import os
import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Any, Union

CONFIG_FILE = "ngrok_tunnels.json"

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {}

def save_config(config: Dict[str, Any]) -> None:
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

class RequestHandler(BaseHTTPRequestHandler):
    config = load_config()
    session = None

    async def create_listener(self, protocol: str, forwards_to: str) -> ngrok.Listener:
        if not self.session:
            self.session = await ngrok.SessionBuilder().authtoken_from_env().metadata("Dynamic Tunnel Creator").connect()
        
        if protocol == "http":
            listener = await self.session.http_endpoint().forwards_to(forwards_to).metadata("example http listener metadata").listen()
        else:
            listener = await self.session.tcp_endpoint().forwards_to(forwards_to).metadata("example tcp listener metadata").listen()
        
        self.config[listener.url()] = {"metadata": listener.metadata(), "protocol": protocol, "forwards_to": forwards_to}
        save_config(self.config)
        
        return listener

    async def handle_create_tunnel(self, protocol: str, forwards_to: str):
        listener = await self.create_listener(protocol, forwards_to)
        self.respond(200, {"url": listener.url(), "metadata": listener.metadata(), "protocol": protocol})

    def do_GET(self):
        if self.path == "/tunnels":
            self.respond(200, self.config)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        request = json.loads(post_data)

        protocol = request.get("protocol")
        forwards_to = request.get("forwards_to")

        if protocol and forwards_to:
            asyncio.run(self.handle_create_tunnel(protocol, forwards_to))
        else:
            self.respond(400, {"error": "Invalid request. 'protocol' and 'forwards_to' are required."})

    def do_DELETE(self):
        path_parts = self.path.split("/")
        if len(path_parts) == 3 and path_parts[1] == "tunnels":
            url = path_parts[2]
            if url in self.config:
                del self.config[url]
                save_config(self.config)
                self.respond(200, {"message": f"Tunnel {url} deleted."})
            else:
                self.respond(404, {"error": "Tunnel not found."})
        else:
            self.respond(400, {"error": "Invalid request."})

    def respond(self, status: int, data: Dict[str, Union[str, Dict]]):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

async def setup_listener():
    server_address = ('localhost', 8080)
    httpd = HTTPServer(server_address, RequestHandler)
    logging.info("Starting HTTP server on port 8080...")
    
    session = await ngrok.SessionBuilder().authtoken_from_env().metadata("API Server").connect()
    listener = await session.http_endpoint().forwards_to("localhost:8080").metadata("API Server Endpoint").listen()
    logging.info(f"ngrok tunnel opened at {listener.url()}")

    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    # Keep the async function alive to maintain the ngrok session
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        running_loop = asyncio.get_running_loop()
        running_loop.create_task(setup_listener())
    except RuntimeError:
        asyncio.run(setup_listener())
