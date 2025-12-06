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


@dataclass
class CameraConfig:
    """Camera configuration."""
    device_id: int = 0  # /dev/video0
    width: int = 1280
    height: int = 720
    fps: int = 10  # For MJPEG capture
    jpeg_quality: int = 85  # JPEG compression quality (0-100)


@dataclass
class TimelapseConfig:
    """Timelapse configuration."""
    enabled: bool = False
    interval_seconds: int = 300  # 5 minutes default
    output_dir: str = "/opt/grow-pi/data/timelapse"
    max_images: int = 1000  # Maximum stored images (rolling buffer)


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

        # Timelapse
        self.timelapse_config = TimelapseConfig()
        self._timelapse_thread: Optional[threading.Thread] = None
        self._timelapse_running = False

        if CV2_AVAILABLE:
            self._init_camera()

    def _init_camera(self) -> bool:
        """Initialize the camera device."""
        try:
            # Use V4L2 backend on Linux for better compatibility
            self._camera = cv2.VideoCapture(self.config.device_id, cv2.CAP_V4L2)

            if not self._camera.isOpened():
                logger.error(f"Failed to open camera device {self.config.device_id}")
                return False

            # Set MJPEG format for efficient capture
            self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

            # Set resolution
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)

            # Set FPS
            self._camera.set(cv2.CAP_PROP_FPS, self.config.fps)

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

                # Encode as JPEG
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality]
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
        if 'jpeg_quality' in kwargs:
            self.config.jpeg_quality = int(kwargs['jpeg_quality'])

        # Reinitialize camera with new settings
        if self._camera:
            self._camera.release()
        self._init_camera()

        return self.get_status()

    # ==========================================
    # Timelapse Functions
    # ==========================================

    def update_timelapse_config(self, **kwargs) -> dict:
        """Update timelapse configuration."""
        if 'enabled' in kwargs:
            self.timelapse_config.enabled = bool(kwargs['enabled'])
        if 'interval_seconds' in kwargs:
            self.timelapse_config.interval_seconds = int(kwargs['interval_seconds'])
        if 'output_dir' in kwargs:
            self.timelapse_config.output_dir = str(kwargs['output_dir'])
        if 'max_images' in kwargs:
            self.timelapse_config.max_images = int(kwargs['max_images'])

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

    def _timelapse_loop(self):
        """Timelapse capture loop."""
        while self._timelapse_running:
            try:
                self._capture_timelapse_image()
            except Exception as e:
                logger.error(f"Timelapse capture error: {e}")

            # Wait for next interval
            time.sleep(self.timelapse_config.interval_seconds)

    def _capture_timelapse_image(self):
        """Capture and save a timelapse image."""
        if not self.is_available:
            return

        # Ensure output directory exists
        os.makedirs(self.timelapse_config.output_dir, exist_ok=True)

        # Capture image
        jpeg_data = self.capture_snapshot()
        if not jpeg_data:
            return

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"timelapse_{timestamp}.jpg"
        filepath = os.path.join(self.timelapse_config.output_dir, filename)

        # Save image
        with open(filepath, 'wb') as f:
            f.write(jpeg_data)

        logger.debug(f"Timelapse image saved: {filename}")

        # Cleanup old images if over limit
        self._cleanup_old_images()

    def _cleanup_old_images(self):
        """Remove oldest images if over max_images limit."""
        try:
            files = sorted([
                f for f in os.listdir(self.timelapse_config.output_dir)
                if f.startswith('timelapse_') and f.endswith('.jpg')
            ])

            while len(files) > self.timelapse_config.max_images:
                oldest = files.pop(0)
                os.remove(os.path.join(self.timelapse_config.output_dir, oldest))
                logger.debug(f"Removed old timelapse image: {oldest}")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def get_timelapse_images(self, limit: int = 50) -> list:
        """Get list of timelapse images."""
        try:
            if not os.path.exists(self.timelapse_config.output_dir):
                return []

            files = sorted([
                f for f in os.listdir(self.timelapse_config.output_dir)
                if f.startswith('timelapse_') and f.endswith('.jpg')
            ], reverse=True)[:limit]

            return [
                {
                    'filename': f,
                    'path': os.path.join(self.timelapse_config.output_dir, f),
                    'timestamp': f.replace('timelapse_', '').replace('.jpg', '')
                }
                for f in files
            ]
        except Exception as e:
            logger.error(f"Error listing timelapse images: {e}")
            return []

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
