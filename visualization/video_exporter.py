"""
visualization/video_exporter.py
-------------------------------
Compiles exported simulation PNG frames into a georeferenced or playback MP4 animation (Task 3).
"""

import os
import cv2
from pathlib import Path
from backend.utils import get_logger

logger = get_logger(__name__)

def export_video_from_frames(png_dir: str | Path, output_file: str | Path, fps: int = 2) -> None:
    """
    Reads all PNG files inside png_dir, sorts them alphabetically,
    and writes them to an MP4 video file using OpenCV's VideoWriter.
    """
    png_path = Path(png_dir)
    out_path = Path(output_file)
    
    if not png_path.exists():
        logger.warning(f"PNG directory does not exist: {png_path}. Skipping video export.")
        return

    # Find and sort all PNG frames
    frames = sorted([f for f in os.listdir(png_path) if f.endswith(".png")])
    if not frames:
        logger.warning(f"No PNG frames found in {png_path}. Skipping video export.")
        return

    first_frame_path = png_path / frames[0]
    img = cv2.imread(str(first_frame_path))
    if img is None:
        logger.error(f"Failed to read first frame at {first_frame_path}")
        return

    height, width, _ = img.shape
    
    # Ensure parent output directory exists
    os.makedirs(out_path.parent, exist_ok=True)
    
    # FourCC code for MP4
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(str(out_path), fourcc, float(fps), (width, height))
    
    try:
        for filename in frames:
            frame_file = png_path / filename
            frame_img = cv2.imread(str(frame_file))
            if frame_img is not None:
                # Resize if frame dimensions differ
                if frame_img.shape[0] != height or frame_img.shape[1] != width:
                    frame_img = cv2.resize(frame_img, (width, height))
                video.write(frame_img)
            else:
                logger.warning(f"Skipped frame {frame_file} (could not read).")
        logger.info(f"Animation successfully exported to {out_path}", extra={"frames": len(frames)})
    except Exception as exc:
        logger.error(f"Failed to compile video animation: {exc}")
    finally:
        video.release()
