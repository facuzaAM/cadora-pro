from __future__ import annotations

import numpy as np
import cv2


class ImagePreprocessor:
    """Robust preprocessor for floor-plan images.

    Handles:
      - AI-generated images (DALL-E, Midjourney, Stable Diffusion)
      - Scanned paper plans (photos, flatbed scans)
      - Digital CAD exports
      - Low-contrast or noisy sources
    """

    TARGET_DPI = 300

    # ── colour / contrast ────────────────────────────────────────────────

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 2:
            return image.copy()
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def enhance_contrast(self, gray: np.ndarray) -> np.ndarray:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    # ── denoising ────────────────────────────────────────────────────────

    def denoise(self, gray: np.ndarray) -> np.ndarray:
        return cv2.fastNlMeansDenoising(gray, h=10)

    def remove_salt_pepper(self, binary: np.ndarray, ksize: int = 3) -> np.ndarray:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        return closed

    # ── binarisation ─────────────────────────────────────────────────────

    def binarize_otsu(self, gray: np.ndarray) -> np.ndarray:
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        return binary

    def binarize_adaptive(
        self, gray: np.ndarray,
        block_size: int = 31, c: int = 10,
    ) -> np.ndarray:
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, block_size, c,
        )

    def binarize_auto(self, gray: np.ndarray) -> np.ndarray:
        """Pick the best binarisation for the image.

        Strategy: compute contrast (std dev). High contrast → Otsu.
        Low contrast (AI / photo) → adaptive with wider block.
        """
        std = float(np.std(gray))
        if std > 50:
            return self.binarize_otsu(gray)
        block = 31 if std > 30 else 51
        c = 10 if std > 30 else 15
        return self.binarize_adaptive(gray, block_size=block, c=c)

    # ── morphological cleanup ────────────────────────────────────────────

    def close_gaps(self, binary: np.ndarray, ksize: int = 3) -> np.ndarray:
        kernel = np.ones((ksize, ksize), np.uint8)
        return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    def thin_noise(self, binary: np.ndarray, min_area: int = 30) -> np.ndarray:
        """Remove small connected components (speckle / texture)."""
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            cv2.bitwise_not(binary), connectivity=8,
        )
        mask = np.zeros_like(binary)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_area:
                mask[labels == i] = 255
        return cv2.bitwise_not(mask)

    def dilate_lines(self, binary: np.ndarray, ksize: int = 2) -> np.ndarray:
        """Slight dilation to reconnect broken line segments."""
        kernel = np.ones((ksize, ksize), np.uint8)
        return cv2.dilate(binary, kernel, iterations=1)

    # ── geometry helpers ─────────────────────────────────────────────────

    def resize_to_dpi(
        self, image: np.ndarray, current_dpi: int = 72,
    ) -> np.ndarray:
        if current_dpi >= self.TARGET_DPI:
            return image
        scale = self.TARGET_DPI / current_dpi
        w = int(image.shape[1] * scale)
        h = int(image.shape[0] * scale)
        return cv2.resize(image, (w, h), interpolation=cv2.INTER_CUBIC)

    def deskew(self, binary: np.ndarray) -> np.ndarray:
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) == 0:
            return binary
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        angle = -angle
        if abs(angle) < 0.3:
            return binary
        h, w = binary.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            binary, matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def remove_grid_lines(self, binary: np.ndarray) -> np.ndarray:
        inv = cv2.bitwise_not(binary)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        h_lines = cv2.morphologyEx(inv, cv2.MORPH_OPEN, h_kernel)
        v_lines = cv2.morphologyEx(inv, cv2.MORPH_OPEN, v_kernel)
        lines = cv2.bitwise_or(h_lines, v_lines)
        return cv2.bitwise_not(cv2.subtract(inv, lines))

    # ── full pipelines ───────────────────────────────────────────────────

    def detect_pipeline(self, image: np.ndarray) -> np.ndarray:
        """Preprocessing optimised for line / door / window detection.

        Works on any source: CAD export, scan, AI image, photo.
        Output: clean binary image with dark lines on white background.
        """
        gray = self.to_grayscale(image)
        gray = self.enhance_contrast(gray)
        gray = self.denoise(gray)
        binary = self.binarize_auto(gray)
        binary = self.remove_salt_pepper(binary, ksize=3)
        binary = self.close_gaps(binary, ksize=3)
        binary = self.thin_noise(binary, min_area=20)
        binary = self.dilate_lines(binary, ksize=2)
        return binary

    def ocr_pipeline(self, image: np.ndarray, dpi: int = 72) -> np.ndarray:
        """Preprocessing optimised for OCR text extraction."""
        gray = self.to_grayscale(image)
        gray = self.resize_to_dpi(gray, dpi)
        gray = self.enhance_contrast(gray)
        gray = self.denoise(gray)
        binary = self.binarize_auto(gray)
        binary = self.deskew(binary)
        return binary

    def pipeline(self, image: np.ndarray, dpi: int = 72) -> np.ndarray:
        """Legacy alias — same as ocr_pipeline."""
        return self.ocr_pipeline(image, dpi)
