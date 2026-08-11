from __future__ import annotations

import cv2
import numpy as np


class ImagePreprocessor:
    """Robust preprocessor for floor-plan images.

    Handles:
      - AI-generated images (DALL-E, Midjourney, Stable Diffusion)
      - Scanned paper plans (photos, flatbed scans)
      - Digital CAD exports
      - Low-contrast or noisy sources

    Every binary output follows a single invariant polarity: **dark ink on a
    white background** (walls are black, background is white). The detection
    engines all depend on that contract.
    """

    TARGET_DPI = 300

    # OCR work resolution. Images larger than this are downscaled so OCR and
    # denoising never blow up on huge uploads (e.g. 6000×8000 scans).
    OCR_MAX_DIM = 3000
    # Very small images are upscaled so thin text remains legible to OCR.
    OCR_MIN_UPSCALE = 1400

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

    # ── binarisation ─────────────────────────────────────────────────────

    def binarize_otsu(self, gray: np.ndarray) -> np.ndarray:
        # THRESH_BINARY: dark strokes -> 0 (black ink), background -> 255.
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        return binary

    def binarize_adaptive(
        self, gray: np.ndarray,
        block_size: int = 31, c: int = 10,
    ) -> np.ndarray:
        # THRESH_BINARY (NOT _INV): dark strokes -> 0, the same polarity as
        # binarize_otsu, so every later stage sees dark ink on white.
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, c,
        )

    def binarize_auto(self, gray: np.ndarray) -> np.ndarray:
        """Pick the best binarisation for the image.

        Both branches return the same polarity: dark ink on white.

        Strategy: compute contrast (std dev). High contrast → Otsu.
        Low contrast (AI / photo) → adaptive with wider block.
        """
        std = float(np.std(gray))
        if std > 50:
            return self.binarize_otsu(gray)
        block = 31 if std > 30 else 51
        c = 10 if std > 30 else 15
        return self.binarize_adaptive(gray, block_size=block, c=c)

    # ── polarity helper ──────────────────────────────────────────────────

    @staticmethod
    def _ink(binary: np.ndarray) -> np.ndarray:
        """Return the ink-as-foreground (white) representation.

        All morphological cleanup is done on this representation so the dark
        ink on white polarity is never accidentally inverted.
        """
        return cv2.bitwise_not(binary)

    # ── morphological cleanup ────────────────────────────────────────────

    def remove_salt_pepper(self, binary: np.ndarray, ksize: int = 3) -> np.ndarray:
        # Closing the ink fills tiny white holes (salt) inside dark strokes.
        # Speckle (pepper) is removed downstream by thin_noise's area filter.
        # Crucially we never OPEN the ink: an opening kernel >= 3px would erase
        # 1px-thin features such as window glass lines.
        kernel = np.ones((ksize, ksize), np.uint8)
        closed = cv2.morphologyEx(self._ink(binary), cv2.MORPH_CLOSE, kernel)
        return cv2.bitwise_not(closed)

    def close_gaps(self, binary: np.ndarray, ksize: int = 3) -> np.ndarray:
        """Bridge small gaps between line segments (scan artifacts)."""
        kernel = np.ones((ksize, ksize), np.uint8)
        closed = cv2.morphologyEx(self._ink(binary), cv2.MORPH_CLOSE, kernel)
        return cv2.bitwise_not(closed)

    def thin_noise(self, binary: np.ndarray, min_area: int = 30) -> np.ndarray:
        """Remove small connected components (speckle / texture)."""
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            self._ink(binary), connectivity=8,
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
        dilated = cv2.dilate(self._ink(binary), kernel, iterations=1)
        return cv2.bitwise_not(dilated)

    # ── geometry helpers ─────────────────────────────────────────────────

    def resize_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Resize to a bounded work resolution for OCR.

        Caps the largest side at ``OCR_MAX_DIM`` so heavy uploads never
        exhaust memory, and upscales very small images so text is readable.
        """
        h, w = image.shape[:2]
        max_side = max(h, w)
        if max_side > self.OCR_MAX_DIM:
            scale = self.OCR_MAX_DIM / max_side
            size = (int(w * scale), int(h * scale))
            return cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        if max_side < self.OCR_MIN_UPSCALE:
            scale = self.OCR_MIN_UPSCALE / max_side
            size = (int(w * scale), int(h * scale))
            return cv2.resize(image, size, interpolation=cv2.INTER_CUBIC)
        return image

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
        coords = np.column_stack(np.where(self._ink(binary) > 0))
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
        """Remove a background graph-paper lattice without touching walls.

        A line counts as a grid line only when it spans nearly the full image
        in its own direction AND there are at least three of them with regular
        spacing in both orientations. Short or irregular lines — genuine
        walls — are never removed.
        """
        if binary.ndim != 2:
            raise ValueError("remove_grid_lines espera una imagen binaria 2D")

        h, w = binary.shape[:2]
        if h < 100 or w < 100:
            return binary

        ink = self._ink(binary)
        row_ink = np.count_nonzero(ink, axis=1)
        col_ink = np.count_nonzero(ink, axis=0)

        grid_rows = np.where(row_ink >= int(w * 0.9))[0]
        grid_cols = np.where(col_ink >= int(h * 0.9))[0]

        if not self._regular_lattice(grid_rows) or not self._regular_lattice(grid_cols):
            return binary

        mask = np.zeros_like(binary)
        mask[grid_rows, :] = 255
        mask[:, grid_cols] = 255
        return cv2.bitwise_or(binary, mask)

    @staticmethod
    def _regular_lattice(lines: np.ndarray) -> bool:
        """True when >=3 lines have a consistent (low-variance) spacing."""
        if len(lines) < 3:
            return False
        diffs = np.diff(lines)
        median = float(np.median(diffs))
        if median <= 0:
            return False
        if np.all(diffs == 0):
            return False
        spread = float(np.max(np.abs(diffs - median)))
        return spread <= median * 0.25

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
        binary = self.remove_grid_lines(binary)
        binary = self.dilate_lines(binary, ksize=2)
        return binary

    def ocr_pipeline(self, image: np.ndarray, dpi: int = 72) -> np.ndarray:
        """Preprocessing optimised for OCR text extraction."""
        gray = self.to_grayscale(image)
        gray = self.resize_for_ocr(gray)
        gray = self.enhance_contrast(gray)
        gray = self.denoise(gray)
        binary = self.binarize_auto(gray)
        binary = self.deskew(binary)
        return binary

    def pipeline(self, image: np.ndarray, dpi: int = 72) -> np.ndarray:
        """Legacy alias — same as ocr_pipeline."""
        return self.ocr_pipeline(image, dpi)
