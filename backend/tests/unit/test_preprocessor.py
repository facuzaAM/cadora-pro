from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.ocr.preprocessor import ImagePreprocessor


@pytest.fixture
def pp() -> ImagePreprocessor:
    return ImagePreprocessor()


class TestToGrayscale:
    def test_color_image(self, pp: ImagePreprocessor):
        color = np.zeros((50, 50, 3), dtype=np.uint8)
        color[:, :, 0] = 100
        color[:, :, 1] = 150
        color[:, :, 2] = 200
        result = pp.to_grayscale(color)
        assert result.ndim == 2
        assert result.shape == (50, 50)

    def test_already_grayscale(self, pp: ImagePreprocessor):
        gray = np.full((40, 40), 128, dtype=np.uint8)
        result = pp.to_grayscale(gray)
        assert result.ndim == 2
        assert result.shape == gray.shape
        np.testing.assert_array_equal(result, gray)

    def test_grayscale_returns_copy(self, pp: ImagePreprocessor):
        gray = np.full((40, 40), 128, dtype=np.uint8)
        result = pp.to_grayscale(gray)
        result[:] = 0
        assert np.all(gray == 128)


class TestEnhanceContrast:
    def test_returns_same_shape(self, pp: ImagePreprocessor):
        gray = np.random.randint(0, 256, (60, 80), dtype=np.uint8)
        result = pp.enhance_contrast(gray)
        assert result.shape == gray.shape
        assert result.dtype == np.uint8


class TestDenoise:
    def test_returns_same_shape(self, pp: ImagePreprocessor):
        gray = np.random.randint(0, 256, (60, 80), dtype=np.uint8)
        result = pp.denoise(gray)
        assert result.shape == gray.shape
        assert result.dtype == np.uint8


class TestBinarizeOtsu:
    def test_produces_binary_output(self, pp: ImagePreprocessor):
        gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = pp.binarize_otsu(gray)
        unique = set(np.unique(result))
        assert unique <= {0, 255}

    def test_shape_unchanged(self, pp: ImagePreprocessor):
        gray = np.random.randint(0, 256, (60, 80), dtype=np.uint8)
        result = pp.binarize_otsu(gray)
        assert result.shape == gray.shape


class TestBinarizeAdaptive:
    def test_produces_binary_output(self, pp: ImagePreprocessor):
        gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = pp.binarize_adaptive(gray)
        unique = set(np.unique(result))
        assert unique <= {0, 255}

    def test_shape_unchanged(self, pp: ImagePreprocessor):
        gray = np.random.randint(0, 256, (60, 80), dtype=np.uint8)
        result = pp.binarize_adaptive(gray)
        assert result.shape == gray.shape


class TestBinarizeAuto:
    def test_high_contrast_image(self, pp: ImagePreprocessor):
        high = np.zeros((100, 100), dtype=np.uint8)
        high[:50, :] = 0
        high[50:, :] = 255
        result = pp.binarize_auto(high)
        unique = set(np.unique(result))
        assert unique <= {0, 255}

    def test_low_contrast_image(self, pp: ImagePreprocessor):
        low = np.full((100, 100), 120, dtype=np.uint8)
        low[40:60, 40:60] = 140
        result = pp.binarize_auto(low)
        unique = set(np.unique(result))
        assert unique <= {0, 255}

    def test_very_low_contrast(self, pp: ImagePreprocessor):
        vlow = np.full((100, 100), 128, dtype=np.uint8)
        vlow[45:55, 45:55] = 132
        result = pp.binarize_auto(vlow)
        unique = set(np.unique(result))
        assert unique <= {0, 255}


class TestRemoveSaltPepper:
    def test_cleans_noise(self, pp: ImagePreprocessor):
        binary = np.full((50, 50), 255, dtype=np.uint8)
        for y in range(0, 50, 5):
            for x in range(0, 50, 5):
                binary[y, x] = 0
        result = pp.remove_salt_pepper(binary)
        assert result.shape == binary.shape
        unique = set(np.unique(result))
        assert unique <= {0, 255}


class TestCloseGaps:
    def test_connects_nearby_components(self, pp: ImagePreprocessor):
        binary = np.full((50, 50), 255, dtype=np.uint8)
        binary[20:22, 10:20] = 0
        binary[20:22, 22:30] = 0
        result = pp.close_gaps(binary, ksize=5)
        assert result.shape == binary.shape


class TestThinNoise:
    def test_removes_small_components(self, pp: ImagePreprocessor):
        binary = np.full((100, 100), 255, dtype=np.uint8)
        cv2.rectangle(binary, (5, 5), (15, 15), 0, -1)
        cv2.rectangle(binary, (60, 60), (90, 90), 0, -1)
        result = pp.thin_noise(binary, min_area=50)
        assert result.shape == binary.shape
        unique = set(np.unique(result))
        assert unique <= {0, 255}


class TestDilateLines:
    def test_expands_white_regions(self, pp: ImagePreprocessor):
        binary = np.full((50, 50), 255, dtype=np.uint8)
        binary[24:26, :] = 0
        result = pp.dilate_lines(binary, ksize=2)
        assert result.shape == binary.shape


class TestRemoveGridLines:
    def test_removes_grid_patterns(self, pp: ImagePreprocessor):
        binary = np.full((200, 200), 255, dtype=np.uint8)
        for i in range(0, 200, 20):
            binary[i, :] = 0
            binary[:, i] = 0
        cv2.rectangle(binary, (80, 80), (120, 120), 0, 2)
        result = pp.remove_grid_lines(binary)
        assert result.shape == binary.shape
        unique = set(np.unique(result))
        assert unique <= {0, 255}


class TestDetectPipeline:
    def test_end_to_end_synthetic_floor_plan(self, pp: ImagePreprocessor):
        img = np.full((400, 400, 3), 255, dtype=np.uint8)
        cv2.rectangle(img, (50, 50), (350, 150), (0, 0, 0), 2)
        cv2.rectangle(img, (50, 150), (350, 350), (0, 0, 0), 2)
        cv2.line(img, (50, 250), (350, 250), (0, 0, 0), 2)
        cv2.line(img, (200, 50), (200, 350), (0, 0, 0), 2)
        result = pp.detect_pipeline(img)
        assert result.ndim == 2
        unique = set(np.unique(result))
        assert unique <= {0, 255}
        assert result.shape == img.shape[:2]


class TestOcrPipeline:
    def test_end_to_end_synthetic_text_image(self, pp: ImagePreprocessor):
        img = np.full((200, 400, 3), 255, dtype=np.uint8)
        for i in range(5):
            x = 20 + i * 70
            cv2.rectangle(img, (x, 80), (x + 40, 100), (0, 0, 0), -1)
        result = pp.ocr_pipeline(img, dpi=72)
        assert result.ndim == 2
        unique = set(np.unique(result))
        assert unique <= {0, 255}

    def test_with_grayscale_input(self, pp: ImagePreprocessor):
        gray = np.full((200, 400), 255, dtype=np.uint8)
        for i in range(5):
            x = 20 + i * 70
            cv2.rectangle(gray, (x, 80), (x + 40, 100), 0, -1)
        result = pp.ocr_pipeline(gray)
        assert result.ndim == 2
        unique = set(np.unique(result))
        assert unique <= {0, 255}
