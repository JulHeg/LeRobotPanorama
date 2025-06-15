"""
debug_shell.py - interactively replay step1…stepN with smooth 1-second moves.

Example launch:
python debug_shell.py --robot.type=so101_follower --robot.port=COM4 --robot.cameras="{}" --robot.id=my_awesome_follower_arm --step_folder="robot_steps" --num_steps=6 --interp_seconds=1.0 --fps=60
"""

import json
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from pprint import pformat

import draccus
import numpy as np

# lerobot imports -----------------------------------------------------------
from lerobot.common.robots import RobotConfig, make_robot_from_config
from lerobot.common.utils.robot_utils import busy_wait
from lerobot.common.utils.utils import init_logging

# register follower classes so the factory recognises them
from lerobot.common.robots import (  # noqa: F401
    so100_follower,
    so101_follower,
)

# ---------------------------------------------------------------------------
@dataclass
class DebugConfig:
    robot: RobotConfig
    step_folder: str = "robot_steps"
    num_steps: int = 6
    interp_seconds: float = 1.0   # duration of each transition
    fps: int = 60                 # control-loop frequency


# ---------------------------------------------------------------------------
def _load_pose(step_dir: Path, n: int) -> dict[str, float]:
    file = step_dir / f"step{n}.json"
    if not file.exists():
        raise FileNotFoundError(f"Pose file '{file}' not found.")
    return json.loads(file.read_text())


def _interpolate_move(robot, start: dict[str, float], end: dict[str, float], seconds: float, fps: int):
    """Linearly interpolate from *start* to *end* over *seconds* seconds."""
    if seconds <= 0:
        robot.send_action(end)
        return

    joints = list(end.keys())
    start_v = np.array([start[j] for j in joints], dtype=np.float64)
    end_v   = np.array([end[j]   for j in joints], dtype=np.float64)

    frames = int(seconds * fps)
    for f in range(frames):
        α = (f + 1) / frames          # 0 → 1 inclusive of endpoint
        pose_vec = (1 - α) * start_v + α * end_v
        robot.send_action(dict(zip(joints, pose_vec)))
        busy_wait(1.0 / fps)

    # Make sure we finish exactly on the final pose
    robot.send_action(end)


# ---------------------------------------------------------------------------
@draccus.wrap()
def debug_shell(cfg: DebugConfig):
    init_logging()
    logging.info("Debug shell config:\n%s", pformat(asdict(cfg)))

    step_dir = Path(cfg.step_folder)
    if not step_dir.exists():
        logging.error("Step folder '%s' does not exist.", step_dir)
        sys.exit(1)

    robot = make_robot_from_config(cfg.robot)
    robot.connect()

    prompt = f"step (1–{cfg.num_steps}, q to quit) > "
    last_pose = None  # remember where the arm is after each command

    try:
        while True:
            try:
                user = input(prompt).strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break

            if user in {"q", "quit", "exit"}:
                break
            if not user.isdigit() or not (1 <= int(user) <= cfg.num_steps):
                print(f"Enter a number 1–{cfg.num_steps} or 'q'.")
                continue

            idx = int(user)
            try:
                target_pose = _load_pose(step_dir, idx)
            except FileNotFoundError as e:
                print(e)
                continue

            if last_pose is None:
                robot.send_action(target_pose)        # first move: no interpolation
            else:
                _interpolate_move(robot, last_pose, target_pose,
                                  cfg.interp_seconds, cfg.fps)
            last_pose = target_pose
            print(f"Arrived at step{idx}.json")
    finally:
        robot.disconnect()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    debug_shell()
