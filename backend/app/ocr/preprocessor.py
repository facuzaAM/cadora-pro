from __future__ import annotations

import math

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
        """Correct small rotations so axis-aligned detection can run.

        Floor plans are scanned/CAD-exported almost axis-aligned; a 0.3-1.0
        degree tilt is enough to pixelate walls and break the gap scanning of
        the door/window detectors. We estimate the dominant skew from long
        near-horizontal/near-vertical lines and rotate it back, filling the
        border with the background colour.
        """
        angle = self._estimate_skew(binary)
        if abs(angle) < 0.15:
            return binary
        return self._rotate(binary, angle)

    @staticmethod
    def _rotate(binary: np.ndarray, angle: float) -> np.ndarray:
        h, w = binary.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            binary, matrix, (w, h),
            flags=cv2.INTER_NEAREST,
            borderValue=255,
        )

    @staticmethod
    def _estimate_skew(binary: np.ndarray) -> float:
        """Return the dominant rotation angle in degrees from long lines."""
        h, w = binary.shape[:2]
        if h < 200 or w < 200:
            return 0.0
        diag = float(np.hypot(h, w))
        # Binary invariant is dark ink on white bg, but HoughLines votes on
        # non-zero pixels, so feed it the ink (inverted) representation. The
        # 1-deg theta step biases the median onto a whole degree and made
        # already-aligned plans rotate by ~1 deg, so use a finer step and
        # weight every line by its vote count so short noise (arcs, corners)
        # can never outvote the long wall edges.
        lines = cv2.HoughLinesWithAccumulator(
            cv2.bitwise_not(binary), rho=1, theta=np.pi / 720,
            threshold=int(diag * 0.08),
        )
        if lines is None:
            return 0.0
        deviations: list[float] = []
        weights: list[float] = []
        best_line: tuple[float, float] | None = None
        best_vote = 0.0
        for rho, theta, vote in np.asarray(lines).reshape(-1, 3):
            deg = math.degrees(theta)
            if 78 <= deg <= 102:
                deviations.append(deg - 90)
            elif deg <= 12:
                deviations.append(deg)
            elif deg >= 168:
                deviations.append(deg - 180)
            else:
                continue
            weights.append(float(vote))
            if vote > best_vote:
                best_vote = float(vote)
                best_line = (float(rho), float(theta))
        if len(deviations) < 4:
            return 0.0
        dev_arr = np.asarray(deviations)
        w_arr = np.asarray(weights)
        order = np.argsort(dev_arr)
        dev_arr, w_arr = dev_arr[order], w_arr[order]
        total = w_arr.sum()
        half = total / 2.0
        cumulative = np.cumsum(w_arr)
        idx = int(np.searchsorted(cumulative, half))
        idx = min(idx, len(dev_arr) - 1)
        median = float(dev_arr[idx])

        refined = ImagePreprocessor._refine_best_line(binary, best_line)
        if refined is not None and abs(refined - median) <= 2.0:
            return refined
        return median

    @staticmethod
    def _refine_best_line(
        binary: np.ndarray, best_line: tuple[float, float] | None,
    ) -> float | None:
        """Fit the strongest near-axis line's ink for sub-degree accuracy.

        HoughLines quantizes theta (here 0.25 deg), which leaves a residual
        tilt that can drift a wall out of the door/window scan band. Fitting
        the ink of the strongest wall edge with cv2.fitLine recovers the
        angle to a fraction of a degree.
        """
        if best_line is None:
            return None
        rho, theta = best_line
        ink = cv2.bitwise_not(binary)
        ys, xs = np.nonzero(ink)
        if xs.size < 20:
            return None
        cos, sin = math.cos(theta), math.sin(theta)
        d = np.abs(xs * cos + ys * sin - rho)
        mask = d <= 4
        pts = np.stack([xs[mask], ys[mask]], axis=1).astype(np.float32)
        if len(pts) < 100:
            return None
        vx, vy = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01).flatten()[:2]
        angle = math.degrees(math.atan2(vy, vx))
        return float(((angle + 45.0) % 90.0) - 45.0)

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

        h_grid_mask = np.zeros_like(ink)
        h_grid_mask[grid_rows, :] = 255
        v_grid_mask = np.zeros_like(ink)
        v_grid_mask[:, grid_cols] = 255

        # Grid lines are 1px and span the image; walls are thick bounded
        # strokes. A 3-element directional erosion erases the thin grid but
        # keeps ink that is part of a stroke >=3px tall/wide (a wall crossing
        # the grid). Erasing only those thin pixels stops a full-column wipe
        # from punching holes through the walls every grid period.
        keep_vertical = cv2.erode(ink, np.ones((3, 1), np.uint8))
        keep_horizontal = cv2.erode(ink, np.ones((1, 3), np.uint8))

        grid = np.zeros_like(ink)
        grid[(ink == 255) & (h_grid_mask == 255) & (keep_vertical == 0)] = 255
        grid[(ink == 255) & (v_grid_mask == 255) & (keep_horizontal == 0)] = 255

        result = binary.copy()
        result[grid == 255] = 255
        return result

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
        """Preprocessing optimised for line / wall detection.

        Works on any source: CAD export, scan, AI image, photo.
        Output: clean binary image with dark lines on white background.

        Closing and dilation bridge small breaks so fragmented walls group
        into single clean strokes. Door/window detectors must NOT use this
        output for gap scanning: the same closing bridges the narrow gap
        between a window's two glass lines, fusing them into a solid block
        that reads as wall and hides the opening. Use ``detect_pipeline_pair``
        which also yields a gap-preserving "fine" binary.
        """
        walls, _ = self.detect_pipeline_pair(image)
        return walls

    def detect_pipeline_pair(
        self, image: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(walls_binary, fine_binary)`` from one preprocessing pass.

        Both share the expensive grayscale/contrast/denoise/binarise/deskew
        work (so they are pixel-aligned), then diverge:

        - ``walls_binary``: closing + dilation bridge small breaks so walls
          group into clean continuous strokes (line detection).
        - ``fine_binary``: no closing/dilation, so narrow gaps and 1px-thin
          glass lines keep their true geometry (door/window gap scanning).
        """
        gray = self.to_grayscale(image)
        gray = self.enhance_contrast(gray)
        gray = self.denoise(gray)
        base = self.binarize_auto(gray)

        # Deskew the shared base once so both outputs stay aligned.
        angle = self._estimate_skew(base)
        if abs(angle) >= 0.15:
            base = self._rotate(base, angle)
        base = self.remove_grid_lines(base)

        # Fine: preserve gaps. Only drop speckle; never close or dilate.
        fine = self.thin_noise(base, min_area=20)

        # Walls: bridge small breaks, then recover stroke solidity.
        walls = self.remove_salt_pepper(base, ksize=3)
        walls = self.close_gaps(walls, ksize=3)
        walls = self.thin_noise(walls, min_area=20)
        walls = self.dilate_lines(walls, ksize=2)

        return walls, fine

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
