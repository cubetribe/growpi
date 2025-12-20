"""
Camera Service for Webcam Snapshots and Timelapse

Provides:
- Single frame capture from USB webcam
- Timelapse configuration and capture
- MJPEG format for efficient transfer
"""

import io
import logging
import os
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# OpenCV availability check
CV2_AVAILABLE = False
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV (cv2) not available - camera features disabled")


def find_lifecam_device() -> int:
    """
    Find Microsoft LifeCam HD-3000 device ID dynamically.

    USB cameras can change device numbers after reboot/reconnect.
    This function finds the camera by name instead of hardcoded ID.

    Returns:
        Device ID (0, 1, etc.) or 0 as fallback
    """
    import subprocess
    import re

    try:
        result = subprocess.run(
            ['v4l2-ctl', '--list-devices'],
            capture_output=True,
            text=True,
            timeout=5
        )

        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if 'LifeCam' in line or 'lifecam' in line.lower():
                # Next non-empty line contains /dev/videoX
                for j in range(i + 1, min(i + 3, len(lines))):
                    match = re.search(r'/dev/video(\d+)', lines[j])
                    if match:
                        device_id = int(match.group(1))
                        logger.info(f"Auto-detected LifeCam at /dev/video{device_id}")
                        return device_id

        logger.warning("LifeCam not found by name, trying fallback detection")

        # Fallback: Try video0, video1, video2
        if CV2_AVAILABLE:
            for dev_id in [0, 1, 2]:
                cap = cv2.VideoCapture(dev_id, cv2.CAP_V4L2)
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        logger.info(f"Fallback: Found working camera at /dev/video{dev_id}")
                        return dev_id

    except Exception as e:
        logger.error(f"Camera auto-detection failed: {e}")

    logger.warning("No camera found, defaulting to device 0")
    return 0


@dataclass
class CameraConfig:
    """Camera configuration."""
    device_id: int = -1  # -1 = auto-detect LifeCam, or specific device number
    width: int = 1920
    height: int = 1080
    preview_fps: int = 2  # Low FPS for live preview (resource-friendly)
    preview_jpeg_quality: int = 70  # Lower quality OK for preview
    timelapse_jpeg_quality: int = 95  # High quality for timelapse photos


@dataclass
class TimelapseConfig:
    """Timelapse configuration."""
    enabled: bool = False
    interval_seconds: int = 300  # 5 minutes default
    output_dir: str = "/opt/grow-pi/data/timelapse"
    max_images: int = 1000  # Maximum stored images (rolling buffer)
    # v6.17.0: Brightness detection for dark image filtering
    skip_dark_images: bool = True
    brightness_threshold: int = 15  # 0-255, images below this average are "too dark"
    min_bright_pixels_percent: float = 10.0  # At least X% of pixels must be above threshold


class CameraService:
    """
    USB Webcam service for capturing images.

    Usage:
        camera = CameraService()
        if camera.is_available:
            jpeg_bytes = camera.capture_snapshot()
    """

    def __init__(self, config: Optional[CameraConfig] = None):
        """Initialize camera service."""
        self.config = config or CameraConfig()
        self._camera: Optional['cv2.VideoCapture'] = None
        self._lock = threading.Lock()
        self._initialized = False
        self._last_capture_time = 0
        self._min_capture_interval = 0.1  # 100ms minimum between captures

        # Timelapse - AUTO-ENABLE on service start
        self.timelapse_config = TimelapseConfig(
            enabled=True,         # AUTO-ENABLED on startup
            interval_seconds=600  # 10 minutes default
        )
        self._timelapse_thread: Optional[threading.Thread] = None
        self._timelapse_running = False

        if CV2_AVAILABLE:
            self._init_camera()

            # Auto-start timelapse if camera initialized successfully
            if self._initialized and self.timelapse_config.enabled:
                self._start_timelapse()
                logger.info(f"Timelapse auto-enabled on startup (interval: {self.timelapse_config.interval_seconds}s)")

    def _init_camera(self) -> bool:
        """Initialize the camera device."""
        try:
            # Auto-detect device if set to -1
            if self.config.device_id == -1:
                self.config.device_id = find_lifecam_device()

            # Use V4L2 backend on Linux for better compatibility
            self._camera = cv2.VideoCapture(self.config.device_id, cv2.CAP_V4L2)

            if not self._camera.isOpened():
                logger.error(f"Failed to open camera device {self.config.device_id}")
                return False

            # Try YUYV (uncompressed) for better quality, fallback to MJPEG
            yuyv_fourcc = cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V')
            mjpeg_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')

            self._camera.set(cv2.CAP_PROP_FOURCC, yuyv_fourcc)
            actual_fourcc = int(self._camera.get(cv2.CAP_PROP_FOURCC))

            if actual_fourcc == yuyv_fourcc:
                logger.info("Camera using YUYV format (uncompressed) for better quality")
            else:
                logger.warning("YUYV not supported, falling back to MJPEG")
                self._camera.set(cv2.CAP_PROP_FOURCC, mjpeg_fourcc)

            # Set resolution
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)

            # Set FPS (low FPS for preview to reduce CPU load)
            self._camera.set(cv2.CAP_PROP_FPS, self.config.preview_fps)

            # Verify settings
            actual_width = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

            logger.info(f"Camera initialized: {actual_width}x{actual_height}")
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Camera initialization error: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """Check if camera is available and working."""
        return CV2_AVAILABLE and self._initialized and self._camera is not None

    def capture_snapshot(self) -> Optional[bytes]:
        """
        Capture a single frame from the camera.

        Returns:
            JPEG image as bytes, or None on failure
        """
        if not self.is_available:
            return None

        with self._lock:
            # Rate limiting
            now = time.time()
            if now - self._last_capture_time < self._min_capture_interval:
                time.sleep(self._min_capture_interval - (now - self._last_capture_time))

            try:
                # Capture frame
                ret, frame = self._camera.read()
                if not ret or frame is None:
                    logger.warning("Failed to capture frame")
                    # Try to reinitialize
                    self._init_camera()
                    return None

                # Rotate 180 degrees (camera is mounted upside down)
                frame = cv2.rotate(frame, cv2.ROTATE_180)

                # Encode as JPEG (lower quality for live preview)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config.preview_jpeg_quality]
                ret, jpeg = cv2.imencode('.jpg', frame, encode_params)

                if not ret:
                    logger.warning("Failed to encode JPEG")
                    return None

                self._last_capture_time = time.time()
                return jpeg.tobytes()

            except Exception as e:
                logger.error(f"Capture error: {e}")
                return None

    def get_status(self) -> dict:
        """Get camera status."""
        status = {
            'available': self.is_available,
            'opencv_available': CV2_AVAILABLE,
            'device_id': self.config.device_id,
            'resolution': f"{self.config.width}x{self.config.height}",
            'timelapse_enabled': self.timelapse_config.enabled,
            'timelapse_interval': self.timelapse_config.interval_seconds
        }

        if self.is_available and self._camera:
            status['actual_width'] = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            status['actual_height'] = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            status['actual_fps'] = int(self._camera.get(cv2.CAP_PROP_FPS))

        return status

    def update_config(self, **kwargs) -> dict:
        """Update camera configuration."""
        if 'width' in kwargs:
            self.config.width = int(kwargs['width'])
        if 'height' in kwargs:
            self.config.height = int(kwargs['height'])
        if 'preview_jpeg_quality' in kwargs:
            self.config.preview_jpeg_quality = int(kwargs['preview_jpeg_quality'])
        if 'timelapse_jpeg_quality' in kwargs:
            self.config.timelapse_jpeg_quality = int(kwargs['timelapse_jpeg_quality'])

        # Reinitialize camera with new settings
        if self._camera:
            self._camera.release()
        self._init_camera()

        return self.get_status()

    # ==========================================
    # Timelapse Functions
    # ==========================================

    def update_timelapse_config(self, **kwargs) -> dict:
        """
        Update timelapse configuration.

        v6.17.0: Added brightness detection parameters.
        """
        if 'enabled' in kwargs:
            self.timelapse_config.enabled = bool(kwargs['enabled'])
        if 'interval_seconds' in kwargs:
            # Clamp to valid range (30s - 600s)
            interval = int(kwargs['interval_seconds'])
            self.timelapse_config.interval_seconds = max(30, min(600, interval))
        if 'output_dir' in kwargs:
            self.timelapse_config.output_dir = str(kwargs['output_dir'])
        if 'max_images' in kwargs:
            self.timelapse_config.max_images = int(kwargs['max_images'])
        # v6.17.0: New brightness detection parameters
        if 'skip_dark_images' in kwargs:
            self.timelapse_config.skip_dark_images = bool(kwargs['skip_dark_images'])
        if 'brightness_threshold' in kwargs:
            # Clamp to valid range (0-255)
            threshold = int(kwargs['brightness_threshold'])
            self.timelapse_config.brightness_threshold = max(0, min(255, threshold))
        if 'min_bright_pixels_percent' in kwargs:
            # Clamp to valid range (0-100)
            percent = float(kwargs['min_bright_pixels_percent'])
            self.timelapse_config.min_bright_pixels_percent = max(0.0, min(100.0, percent))

        # Start/stop timelapse thread based on enabled status
        if self.timelapse_config.enabled and not self._timelapse_running:
            self._start_timelapse()
        elif not self.timelapse_config.enabled and self._timelapse_running:
            self._stop_timelapse()

        return asdict(self.timelapse_config)

    def _start_timelapse(self):
        """Start timelapse capture thread."""
        if self._timelapse_running:
            return

        self._timelapse_running = True
        self._timelapse_thread = threading.Thread(target=self._timelapse_loop, daemon=True)
        self._timelapse_thread.start()
        logger.info(f"Timelapse started (interval: {self.timelapse_config.interval_seconds}s)")

    def _stop_timelapse(self):
        """Stop timelapse capture thread."""
        self._timelapse_running = False
        if self._timelapse_thread:
            self._timelapse_thread.join(timeout=5)
        logger.info("Timelapse stopped")

    def _analyze_brightness(self, frame) -> dict:
        """
        Analyze frame brightness for darkness detection.

        Uses grayscale conversion and histogram analysis to determine
        if an image is too dark to save (e.g., when grow lights are off).

        Args:
            frame: OpenCV BGR frame

        Returns:
            dict with brightness analysis:
            - average_brightness: 0-255 average pixel value
            - bright_pixel_percent: percentage of pixels above threshold
            - is_too_dark: boolean based on config thresholds
            - threshold: configured threshold value
        """
        import numpy as np

        # Convert to grayscale for brightness analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Calculate average brightness (0-255)
        avg_brightness = float(gray.mean())

        # Calculate percentage of "bright" pixels (above threshold)
        threshold = self.timelapse_config.brightness_threshold
        bright_pixels = int((gray > threshold).sum())
        total_pixels = gray.size
        bright_percent = (bright_pixels / total_pixels) * 100

        # Determine if image is too dark
        # Too dark if: average below threshold OR not enough bright pixels
        is_too_dark = (
            avg_brightness < threshold or
            bright_percent < self.timelapse_config.min_bright_pixels_percent
        )

        return {
            'average_brightness': round(avg_brightness, 1),
            'bright_pixel_percent': round(bright_percent, 1),
            'is_too_dark': is_too_dark,
            'threshold': threshold,
            'min_bright_percent': self.timelapse_config.min_bright_pixels_percent
        }

    def _timelapse_loop(self):
        """Timelapse capture loop."""
        while self._timelapse_running:
            try:
                self._capture_timelapse_image()
            except Exception as e:
                logger.error(f"Timelapse capture error: {e}")

            # Wait for next interval
            time.sleep(self.timelapse_config.interval_seconds)

    def _capture_timelapse_image(self) -> dict:
        """
        Capture and save a timelapse image with darkness detection.

        v6.17.0: Added brightness check to skip dark images.
        Images are now organized in date-based folders.

        Returns:
            dict with capture result:
            - success: bool
            - reason: str (if failed)
            - filename: str (if success)
            - brightness: dict (brightness analysis)
        """
        if not self.is_available:
            return {'success': False, 'reason': 'camera_unavailable'}

        # Capture frame directly (not via capture_snapshot to get raw frame)
        with self._lock:
            try:
                ret, frame = self._camera.read()
                if not ret or frame is None:
                    logger.warning("Timelapse: Failed to capture frame")
                    return {'success': False, 'reason': 'capture_failed'}

                # Rotate 180 degrees (camera mounted upside down)
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            except Exception as e:
                logger.error(f"Timelapse capture error: {e}")
                return {'success': False, 'reason': str(e)}

        # Check brightness if darkness filter is enabled
        brightness_info = None
        if self.timelapse_config.skip_dark_images:
            brightness_info = self._analyze_brightness(frame)
            if brightness_info['is_too_dark']:
                logger.debug(
                    f"Timelapse: Skipped dark image "
                    f"(avg={brightness_info['average_brightness']}, "
                    f"bright={brightness_info['bright_pixel_percent']}%)"
                )
                return {
                    'success': False,
                    'reason': 'too_dark',
                    'brightness': brightness_info
                }

        # Encode as JPEG (high quality for timelapse archival)
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config.timelapse_jpeg_quality]
        ret, jpeg = cv2.imencode('.jpg', frame, encode_params)
        if not ret:
            return {'success': False, 'reason': 'encode_failed'}

        # Create date-based folder structure
        date_folder = datetime.now().strftime("%Y-%m-%d")
        folder_path = os.path.join(self.timelapse_config.output_dir, date_folder)
        os.makedirs(folder_path, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"timelapse_{timestamp}.jpg"
        filepath = os.path.join(folder_path, filename)

        # Save image
        try:
            with open(filepath, 'wb') as f:
                f.write(jpeg.tobytes())
            logger.debug(f"Timelapse image saved: {date_folder}/{filename}")
        except Exception as e:
            logger.error(f"Timelapse save error: {e}")
            return {'success': False, 'reason': str(e)}

        # Cleanup old images if over limit
        self._cleanup_old_images()

        return {
            'success': True,
            'filename': filename,
            'folder': date_folder,
            'path': filepath,
            'timestamp': timestamp,
            'brightness': brightness_info
        }

    def _cleanup_old_images(self):
        """
        Remove oldest images if over max_images limit.

        v6.17.0: Updated to handle date-based folder structure.
        """
        try:
            base_dir = self.timelapse_config.output_dir
            if not os.path.exists(base_dir):
                return

            # Collect all images from all date folders
            all_images = []
            for folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, folder)
                if os.path.isdir(folder_path):
                    for f in os.listdir(folder_path):
                        if f.startswith('timelapse_') and f.endswith('.jpg'):
                            all_images.append({
                                'folder': folder,
                                'filename': f,
                                'path': os.path.join(folder_path, f)
                            })

            # Sort by filename (which contains timestamp)
            all_images.sort(key=lambda x: x['filename'])

            # Remove oldest images if over limit
            while len(all_images) > self.timelapse_config.max_images:
                oldest = all_images.pop(0)
                os.remove(oldest['path'])
                logger.debug(f"Removed old timelapse: {oldest['folder']}/{oldest['filename']}")

                # Remove empty folders
                folder_path = os.path.join(base_dir, oldest['folder'])
                if os.path.isdir(folder_path) and not os.listdir(folder_path):
                    os.rmdir(folder_path)
                    logger.debug(f"Removed empty folder: {oldest['folder']}")

        except Exception as e:
            logger.error(f"Timelapse cleanup error: {e}")

    def get_timelapse_images(self, limit: int = 50, date_folder: str = None) -> list:
        """
        Get list of timelapse images.

        v6.17.0: Updated to handle date-based folder structure.

        Args:
            limit: Maximum number of images to return
            date_folder: Optional date filter (YYYY-MM-DD format)

        Returns:
            List of image metadata dicts
        """
        try:
            base_dir = self.timelapse_config.output_dir
            if not os.path.exists(base_dir):
                return []

            images = []

            if date_folder:
                # List images from specific date folder
                folder_path = os.path.join(base_dir, date_folder)
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    for f in os.listdir(folder_path):
                        if f.startswith('timelapse_') and f.endswith('.jpg'):
                            images.append({
                                'filename': f,
                                'folder': date_folder,
                                'path': f"/api/camera/timelapse/image/{date_folder}/{f}",
                                'timestamp': f.replace('timelapse_', '').replace('.jpg', '')
                            })
            else:
                # List images from all date folders (most recent first)
                folders = sorted([
                    d for d in os.listdir(base_dir)
                    if os.path.isdir(os.path.join(base_dir, d))
                ], reverse=True)

                for folder in folders:
                    folder_path = os.path.join(base_dir, folder)
                    for f in sorted(os.listdir(folder_path), reverse=True):
                        if f.startswith('timelapse_') and f.endswith('.jpg'):
                            images.append({
                                'filename': f,
                                'folder': folder,
                                'path': f"/api/camera/timelapse/image/{folder}/{f}",
                                'timestamp': f.replace('timelapse_', '').replace('.jpg', '')
                            })
                            if len(images) >= limit:
                                break
                    if len(images) >= limit:
                        break

            # Sort by timestamp descending and limit
            images.sort(key=lambda x: x['timestamp'], reverse=True)
            return images[:limit]

        except Exception as e:
            logger.error(f"Error listing timelapse images: {e}")
            return []

    def get_timelapse_folders(self) -> list:
        """
        Get list of available date folders.

        Returns:
            List of folder metadata dicts with name and image count
        """
        try:
            base_dir = self.timelapse_config.output_dir
            if not os.path.exists(base_dir):
                return []

            folders = []
            for d in sorted(os.listdir(base_dir), reverse=True):
                folder_path = os.path.join(base_dir, d)
                if os.path.isdir(folder_path):
                    # Count images in folder
                    count = len([
                        f for f in os.listdir(folder_path)
                        if f.startswith('timelapse_') and f.endswith('.jpg')
                    ])
                    if count > 0:  # Only include non-empty folders
                        folders.append({
                            'name': d,
                            'image_count': count
                        })
            return folders
        except Exception as e:
            logger.error(f"Error listing timelapse folders: {e}")
            return []

    def get_timelapse_stats(self) -> dict:
        """
        Get timelapse statistics including config, storage, and counts.

        Returns:
            dict with stats
        """
        folders = self.get_timelapse_folders()
        total_images = sum(f['image_count'] for f in folders)

        return {
            'config': asdict(self.timelapse_config),
            'is_running': self._timelapse_running,
            'total_folders': len(folders),
            'total_images': total_images,
            'storage_path': self.timelapse_config.output_dir,
            'storage_size_mb': self._get_storage_size()
        }

    def _get_storage_size(self) -> float:
        """Calculate total storage used by timelapse images in MB."""
        total_size = 0
        base_dir = self.timelapse_config.output_dir

        if os.path.exists(base_dir):
            for root, dirs, files in os.walk(base_dir):
                for f in files:
                    if f.endswith('.jpg'):
                        try:
                            total_size += os.path.getsize(os.path.join(root, f))
                        except OSError:
                            pass

        return round(total_size / (1024 * 1024), 2)

    def test_brightness(self) -> dict:
        """
        Test brightness detection with current camera frame.

        Returns:
            dict with brightness analysis and whether image would be saved
        """
        if not self.is_available:
            return {'success': False, 'error': 'camera_unavailable'}

        with self._lock:
            try:
                ret, frame = self._camera.read()
                if not ret or frame is None:
                    return {'success': False, 'error': 'capture_failed'}

                # Rotate 180 degrees
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            except Exception as e:
                return {'success': False, 'error': str(e)}

        # Analyze brightness
        brightness_info = self._analyze_brightness(frame)

        return {
            'success': True,
            'brightness': brightness_info,
            'would_save': not brightness_info['is_too_dark']
        }

    def release(self):
        """Release camera resources."""
        self._stop_timelapse()
        if self._camera:
            self._camera.release()
            self._camera = None
            self._initialized = False
        logger.info("Camera released")


# ==========================================
# Singleton Instance
# ==========================================
_camera_service: Optional[CameraService] = None


def get_camera_service() -> CameraService:
    """Get or create singleton CameraService."""
    global _camera_service

    if _camera_service is None:
        _camera_service = CameraService()

    return _camera_service
