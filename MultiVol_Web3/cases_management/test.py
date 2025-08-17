# handle_case.py
from __future__ import annotations
import logging
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rxconfig import config
from typing import List
import asyncio
from pathlib import Path
import json, shlex
import docker
import socket
logger = logging.getLogger(__name__)
def get_self_container():
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")
    hostname = socket.gethostname()
    current_ip_address = socket.gethostbyname(hostname)
    # Check all running containers
    for container in client.containers.list():
        info = container.attrs  # same as container.reload() + container.attrs
        networks = info["NetworkSettings"]["Networks"]
        ip_address = next(iter(networks.values()))["IPAddress"]
        if current_ip_address == ip_address:
            return container
    return None

def get_host_mount_for(path_in_container):
    container = get_self_container()
    if not container:
        raise RuntimeError("Could not find self container from PID")
    for mount in container.attrs["Mounts"]:
        #print(mount)
        if mount["Destination"] == path_in_container:
            return Path(mount["Source"])
    return None
print(Path(__file__).parent.parent.parent / "uploaded_files")

print(get_host_mount_for(str(Path(__file__).parent.parent.parent / "uploaded_files")))
print(get_host_mount_for(str(Path(__file__).parent.parent / "profiles_json")))

current_path_parent = Path(__file__).parent.parent
cases_dir = current_path_parent / "cases"
print(get_host_mount_for(str(current_path_parent / "cases")))

#new_case_dir = cases_dir / case_name.replace(" ", "_")