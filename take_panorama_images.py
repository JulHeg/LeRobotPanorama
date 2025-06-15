"""
player.py - Replay a sequence of recorded poses on a follower arm and take photos.

Example call (Windows):

python take_panorama_images.py ^
    --robot.type=so101_follower ^
    --robot.port=COM4 ^
    --robot.cameras="{}" ^
    --robot.id=my_awesome_follower_arm ^
    --step_folder="robot_steps" ^
    --photo_folder="photos" ^
    --seconds_per_step=4 ^
    --fps=60
"""

import glob
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pprint import pformat
import cv2

import draccus
import imageio.v2 as imageio
import numpy as np

from lerobot.common.robots import RobotConfig, make_robot_from_config
from lerobot.common.utils.robot_utils import busy_wait
from lerobot.common.utils.utils import init_logging
from lerobot.common.robots import (
    so100_follower,
    so101_follower,
)

@dataclass
class PlayerConfig:
    # Existing robot definition
    robot: RobotConfig

    # Where the step*.json files live
    step_folder: str

    # Where photos will be stored
    photo_folder: str = "photos"

    # Control-loop parameters
    fps: int = 60
    seconds_per_step: float = 4.0

    # Photo capture parameters
    num_photos_per_segment: int = 10
    settle_before_photo_s: float = 0.5
    pause_after_photo_s: float = 0.2


# ---------------------------------------------------------------------------

def _load_steps(folder: str) -> list[dict[str, float]]:
    paths = sorted(glob.glob(os.path.join(folder, "step*.json")))
    if len(paths) < 2:
        raise RuntimeError("Need at least two step files to interpolate.")
    return [json.load(open(p, "r")) for p in paths]


def _save_photo(obs: dict[str, object], out_path: str):
    """
    Save the first numpy-array image found in `obs` as PNG.
    """
    for v in obs.values():
        if isinstance(v, np.ndarray):
            imageio.imwrite(out_path, v)
            return
    raise RuntimeError("No image data found in observation; can’t save photo.")


def _interpolate_loop(
    robot,
    steps: list[dict[str, float]],
    cfg: PlayerConfig,
):
    """
    Interpolate poses and take photos.

    Pauses: 0.5 s before each photo (let the arm settle) + 0.2 s after the shot.
    """
    
    joints = list(steps[0].keys())

    os.makedirs(cfg.photo_folder, exist_ok=True)

    # Empty the photo folder before starting
    for filename in os.listdir(cfg.photo_folder):
        file_path = os.path.join(cfg.photo_folder, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            logging.error(f"Error deleting file {file_path}: {e}")

    for seg_idx in range(len(steps) - 1):
        if seg_idx % 2 == 1:
            seconds_per_step = cfg.seconds_per_step
        else:
            seconds_per_step = cfg.seconds_per_step / 6
        frames_total = int(cfg.fps * seconds_per_step)
        photo_frames = np.linspace(
            0, frames_total, cfg.num_photos_per_segment, dtype=int
        )  # inclusive endpoints
        start_vec = np.array([steps[seg_idx][j] for j in joints], dtype=np.float64)
        end_vec   = np.array([steps[seg_idx + 1][j] for j in joints], dtype=np.float64)

        for frame in range(frames_total):
            α = frame / frames_total
            pose_vec = (1 - α) * start_vec + α * end_vec
            action = dict(zip(joints, pose_vec))
            robot.send_action(action)

            # If this frame corresponds to a photo, pause & capture
            if frame in photo_frames and seg_idx % 2 == 1:
                busy_wait(cfg.settle_before_photo_s)  # settle
                filename = os.path.join(
                    cfg.photo_folder, f"seg{seg_idx+1:02d}_p{frame:04d}.jpg"
                )

                cap = cv2.VideoCapture(1)

                # Wait for the camera to initialize
                if not cap.isOpened():
                    raise IOError("Cannot open webcam")

                # Read one frame
                ret, frame = cap.read()

                # Save the frame as an image
                if ret:
                    cv2.imwrite(filename, frame)
                else:
                    print(f"Failed to capture photo for segment {seg_idx + 1}, frame {frame}")
                cap.release()
                busy_wait(cfg.pause_after_photo_s)    # additional pause

            busy_wait(1.0 / cfg.fps)

        # Ensure exact endpoint pose
        robot.send_action(steps[seg_idx + 1])

    # Send final pose once more for safety
    robot.send_action(steps[-1])


# ---------------------------------------------------------------------------

@draccus.wrap()
def player(cfg: PlayerConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))

    steps = _load_steps(cfg.step_folder)
    robot = make_robot_from_config(cfg.robot)

    robot.connect()
    try:
        _interpolate_loop(robot, steps, cfg)
        print("Finished replaying poses and capturing photos.")
    except KeyboardInterrupt:
        pass
    finally:
        robot.disconnect()

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    player()

    command = r"nona -o out -m TIFF template.pto"
    folder = r"photos"
    # append every file name in the folder to the command
    for filename in os.listdir(folder):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            command += f" {os.path.join(folder, filename)}"

    # execute the command
    os.system(command)
    print("Successfully created panorama image")
