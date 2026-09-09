"""Synthetic worker for subprocess watchdog faults. Never imports COM."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--runtime-dir", required=True)
parser.add_argument("--phase", default="finished")
parser.add_argument("--mode", default="hang")
args = parser.parse_args()
sys.path.insert(0, args.runtime_dir)
from aspen_runtime import StageRecorder, atomic_json

recorder = StageRecorder()
if args.mode == "normal":
    for phase in ("creating_com", "opening", "running", "exporting", "closing"):
        recorder.update(phase, synthetic=True)
    recorder.update("finished", lifecycle_clean=True, synthetic=True)
elif args.mode == "crash":
    recorder.update(args.phase, synthetic=True)
    raise SystemExit(7)
elif args.mode == "forged":
    atomic_json(Path(os.environ["ASPEN_RUNTIME_STAGE_FILE"]), {"run_id": "FOREIGN", "owner_token": "FOREIGN", "pid": os.getpid(), "sequence": 99, "phase": "finished", "lifecycle_clean": True})
    time.sleep(60)
else:
    if args.phase != "worker_boot":
        recorder.update(args.phase, synthetic=True)
    time.sleep(60)
