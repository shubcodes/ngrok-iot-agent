# IoT-Agent

This project implements an agent that dynamically creates, lists, and deletes ngrok tunnels through a FastAPI interface. The agent ensures that tunnels are persisted and can be recreated upon restart, making it robust for dynamic IoT applications.

## Features

- Dynamically create ngrok tunnels
- List all active tunnels
- Delete specific tunnels
- Automatically recreate tunnels on agent restart
- Use reserved domains for consistent tunnel URLs (requires ngrok paid plan)

## Prerequisites

- Python
- ngrok account (free for dynamic URLs, paid for reserved domains)
- FastAPI
- Uvicorn

## Setup

1. **Clone the repository**:

2. **Create and activate a virtual environment**:

3. **Install dependencies**:

4. **Set your ngrok authtoken**:
    ```sh
    ngrok authtoken <YOUR_NGROK_AUTHTOKEN>
    ```

5. **Run the agent**:
    ```sh
    python agent.py
    ```

## API Endpoints

### List Tunnels

**Request**: `GET /tunnels`

**Description**: List all active tunnels.

**Response**:
```json
[
    {
        "url": "https://2F334e095e9685.ngrok.app",
        "protocol": "http",
        "forwards_to": "localhost:8001",
        "domain": null
    }
]
```

### Create Tunnel
**Request**: `POST /tunnels`

**Description**: Create a new ngrok tunnel.

**Request Body**:

```json
{
    "protocol": "http",
    "forwards_to": "localhost:8080",
    "domain": "your-reserved-domain.ngrok.io" 
}
```

**Response**:

```json
{
    "url": "https://your-reserved-domain.ngrok.io",
    "protocol": "http",
    "forwards_to": "localhost:8080",
    "domain": "your-reserved-domain.ngrok.io"
}
```
### Delete Tunnel

**Request**: `DELETE /tunnels/{url_part}`

**Description**: Delete a specified tunnel by the main part of the URL.

**Request Body** :

curl -X DELETE https://82916d83f41a.ngrok.app/tunnels/2F334e095e9685

**Response**:
```
json
{
    "detail": "Tunnel deleted"
}
```