from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Union

import httpx

if TYPE_CHECKING:
    import discord

logger = logging.getLogger(__name__)


def should_upload_to_discord(file_path: Path, max_size_mb: float) -> bool:
    return file_path.stat().st_size <= int(max_size_mb * 1024 * 1024)


def upload_to_sharry(file_path: Path) -> str:
    url = os.environ["SHARRY_URL"].rstrip("/")
    user = os.environ["SHARRY_USER"]
    password = os.environ["SHARRY_PASS"]

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{url}/api/v2/open/auth/login",
            headers={"accept": "application/json", "Content-Type": "application/json"},
            json={"account": user, "password": password},
        )
        response.raise_for_status()
        token = response.json()["token"]

        with open(file_path, "rb") as fp:
            response = client.post(
                f"{url}/api/v2/sec/upload",
                headers={"accept": "application/json", "Sharry-Auth": token},
                data={"meta": '{"validity":604800000,"maxViews":30}'},
                files={"file": (file_path.name, fp)},
            )
        response.raise_for_status()
        folder_id = response.json()["id"]

        response = client.post(
            f"{url}/api/v2/sec/share/{folder_id}/publish",
            headers={"accept": "application/json", "Content-Type": "application/json"},
            json={"reuseId": True},
        )
        response.raise_for_status()

        response = client.get(
            f"{url}/api/v2/sec/share/{folder_id}",
            headers={"accept": "application/json"},
        )
        response.raise_for_status()

        publish_id = response.json()["publishInfo"]["id"]
        return f"{url}/app/open/{publish_id}?view=1"


def get_file_delivery(
    file_path: Path,
    max_size_mb: float,
) -> Union["discord.File", str]:
    import discord

    if should_upload_to_discord(file_path, max_size_mb):
        return discord.File(file_path)
    url = upload_to_sharry(file_path)
    logger.info(f"Uploaded {file_path.name} to Sharry: {url}")
    return url
