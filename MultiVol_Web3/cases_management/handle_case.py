# handle_case.py
from __future__ import annotations
from typing import Any
import json
import logging
import shlex
import subprocess
from ..rxconfig import config
from pathlib import Path
from typing import List
logger = logging.getLogger(__name__)


async def after_upload(
    state,
    uploaded_files_names: List[str],
    case_name: str,
    os_value: str,
    mode_value: str
):
    import asyncio
    from pathlib import Path
    import json, shlex
    try:
        current_path_parent = Path(__file__).parent.parent
        cases_dir = current_path_parent / "cases"
        new_case_dir = cases_dir / case_name.replace(" ", "_")
        new_case_dir.mkdir(parents=True, exist_ok=True)
        state.log_append(f"New case directory created: {new_case_dir}")
        logger.info("New case directory created: %s", new_case_dir)
        yield
    except Exception as e:
        err = f"[ERROR] Failed to create case directory {new_case_dir}: {e}"
        state.log_append(err)
        logger.exception(err)
        yield
        return

    try:
        case_details_path = new_case_dir / "case_details.json"
        case_details = {
            "case_name": case_name,
            "case_details": "This is a test case for MultiVol",
            "case_os": os_value,
        }
        with case_details_path.open("w", encoding="utf-8") as f:
            json.dump(case_details, f, indent=4, ensure_ascii=False)
        msg = f"Wrote case details to {case_details_path}"
        state.log_append(msg)
        logger.info(msg)
        yield
    except Exception as e:
        err = f"[ERROR] Failed to write case_details.json: {e}"
        state.log_append(err)
        logger.exception(err)
        yield

    for upload_name in uploaded_files_names:
        try:
            state.log_append(f"File {upload_name} uploaded successfully.")
            logger.info("File %s uploaded successfully.", upload_name)
            yield
            multivol_script = Path(f"{config.cli_multivol_path}") / "main.py"
            symbols_path = Path(__file__).parent.parent / "profiles_json"
            dump_path = Path(upload_name)
            if os_value != "linux":
                command = (
                    f"python3 {shlex.quote(str(multivol_script))} vol3 "
                    f"--dump {shlex.quote(str(dump_path))} "
                    f"--image volatility3 "
                    f"--{shlex.quote(os_value)} "
                    f"--{shlex.quote(mode_value)} "
                    f"--output-path {shlex.quote(str(new_case_dir))} "
                    f"--symbols-path {shlex.quote(str(symbols_path))} "
                    f"--format json"
                )
            else:
                command = (
                    f"python3 {shlex.quote(str(multivol_script))} vol3 "
                    f"--dump {shlex.quote(str(dump_path))} "
                    f"--image volatility3 "
                    f"--{shlex.quote(os_value)} "
                    f"--output-path {shlex.quote(str(new_case_dir))} "
                    f"--format json"
                )
            state.log_append(f"[EXECUTING] {command}")
            logger.info("Executing: %s", command)
            yield

            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            if proc.stdout is not None:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    text = line.decode(errors="ignore").rstrip()
                    if text:
                        state.log_append(f"[post] {text}")
                        yield

            rc = await proc.wait()
            if rc == 0:
                state.log_append("[post] command succeeded")
                logger.info("Command succeeded.")
            else:
                state.log_append(f"[ERROR] command failed with return code {rc}")
                logger.error("Command failed with return code %s", rc)
            yield

        except Exception as e:
            err = f"[ERROR] Exception while processing {upload_name}: {e}"
            state.log_append(err)
            logger.exception(err)
            yield
