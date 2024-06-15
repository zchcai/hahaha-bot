#!/usr/bin/env python3
"""The main module for the Hanabi bot."""

# Imports (standard library)
import os
import sys
import threading
import time

# Imports (3rd-party)
# The "dotenv" module does not work in Python 2
import dotenv
import requests

# Imports (local application)
from src.hanabi_client import HanabiClient
from src.utils import printf

LOGIN_PATH = "/login"
WS_PATH="/ws"
PUBLIC_WEBSITE="hanab.live"

def get_cookies_by_password(url, username, password):
    printf('Authenticating to "' + url + '" with a username of "' + username + '".')
    resp = requests.post(
        url,
        {
            "username": username,
            "password": password,
            # This is normally supposed to be the version of the JavaScript
            # client, but the server will also accept "bot" as a valid version.
            "version": "bot",
        },
        timeout=10
    )

    # Handle failed authentication and other errors.
    if resp.status_code != 200:
        printf("Authentication failed:")
        printf(resp.text)
        sys.exit(1)

    # Scrape the cookie from the response.
    cookie = ""
    for header in resp.headers.items():
        if header[0] == "Set-Cookie":
            cookie = header[1]
            break
    if cookie == "":
        printf("Failed to parse the cookie from the authentication response headers:")
        printf(resp.headers)
        sys.exit(1)

    return cookie

def main():
    """Authenticate, login to the WebSocket server, and run forever."""

    # Check to see if the ".env" file exists.
    env_path = os.path.join(os.path.realpath(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        printf(
            'error: the ".env" file does not exist;'
            'copy the ".env_template" file to ".env" and '
            'edit the values accordingly'
        )
        sys.exit(1)

    # Load environment variables from the ".env" file.
    dotenv.load_dotenv()

    username = os.getenv("HANABI_USERNAME")
    password = os.getenv("HANABI_PASSWORD")
    if username == "" or password == "":
        printf('error: username and/or password is missing the ".env" file')
        sys.exit(1)

    local_url = os.getenv("LOCAL_URL")
    local_port = os.getenv("LOCAL_PORT")
    if local_url == "":
        local_url = "localhost"
    if local_port == "":
        local_port = 80

    # The official site uses HTTPS.
    protocol = "https"
    ws_protocol = "wss"
    host = PUBLIC_WEBSITE

    use_localhost = os.getenv("USE_LOCALHOST")
    if use_localhost == "true":
        # Assume that we are not using a certificate if we are running a local
        # version of the server.
        protocol = "http"
        ws_protocol = "ws"
        host = local_url + ":" + local_port
    elif use_localhost not in ["false", ""]:
        printf(
            'error: "USE_LOCALHOST" should be set to either "true" or "false" '
            'or leave as empty in the ".env" file'
        )
        sys.exit(1)

    url = protocol + "://" + host + LOGIN_PATH
    ws_url = ws_protocol + "://" + host + WS_PATH

    if host == PUBLIC_WEBSITE or len(sys.argv) == 1:
        cookie = get_cookies_by_password(url, username, password)

        # Start!
        HanabiClient(ws_url, cookie)
        return

    # Otherwise, multi-threads.
    for arg in sys.argv:
        if arg.endswith("main.py"):
            threading.Thread(daemon=True,
                             target=HanabiClient,
                             args=(ws_url,
                                   get_cookies_by_password(url, username, password))).start()
        else:
            # Assume using the same string for a robot's password and username.
            threading.Thread(daemon=True,
                             target=HanabiClient,
                             args=(ws_url,
                                   get_cookies_by_password(url, arg, arg))).start()
    while True:
        # Wait for keyboardIntereption
        time.sleep(5)

if __name__ == "__main__":
    main()
