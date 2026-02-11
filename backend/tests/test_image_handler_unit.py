import pytest
import base64
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.utils.image_handler import save_base64_image, load_image_to_base64

@pytest.fixture
def temp_upload_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with patch("app.utils.image_handler.UPLOAD_DIR", tmp_path):
            yield tmp_path

def test_save_base64_image_success(temp_upload_dir):
    # PNG
    data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    url = save_base64_image(data)
    assert url.startswith("/files/")
    assert url.endswith(".png")
    
    filename = url.replace("/files/", "")
    assert (temp_upload_dir / filename).exists()

def test_save_base64_image_different_types(temp_upload_dir):
    # JPEG
    url_jpg = save_base64_image("data:image/jpeg;base64,YWJj")
    assert url_jpg.endswith(".jpg")
    
    # GIF
    url_gif = save_base64_image("data:image/gif;base64,YWJj")
    assert url_gif.endswith(".gif")
    
    # WEBP
    url_webp = save_base64_image("data:image/webp;base64,YWJj")
    assert url_webp.endswith(".webp")
    
    # SVG
    url_svg = save_base64_image("data:image/svg+xml;base64,YWJj")
    assert url_svg.endswith(".svg")

def test_save_base64_image_no_header(temp_upload_dir):
    url = save_base64_image("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    assert url.endswith(".png")

def test_save_base64_image_error(temp_upload_dir):
    with patch("base64.b64decode", side_effect=Exception("Decode error")):
        with pytest.raises(Exception):
            save_base64_image("invalid")

def test_load_image_to_base64_success(temp_upload_dir):
    # Save first
    data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    url = save_base64_image(data)
    
    # Load back
    loaded = load_image_to_base64(url)
    assert loaded == data

def test_load_image_to_base64_not_managed(temp_upload_dir):
    external = "https://example.com/img.png"
    assert load_image_to_base64(external) == external

def test_load_image_to_base64_missing_file(temp_upload_dir):
    url = "/files/missing.png"
    assert load_image_to_base64(url) == url

def test_load_image_to_base64_various_types(temp_upload_dir):
    # JPG
    url = save_base64_image("data:image/jpeg;base64,YWJj")
    loaded = load_image_to_base64(url)
    assert loaded.startswith("data:image/jpeg;base64,")
    
    # GIF
    url = save_base64_image("data:image/gif;base64,YWJj")
    loaded = load_image_to_base64(url)
    assert loaded.startswith("data:image/gif;base64,")

def test_load_image_to_base64_error(temp_upload_dir):
    url = save_base64_image("data:image/png;base64,YWJj")
    with patch("builtins.open", side_effect=Exception("Read error")):
        assert load_image_to_base64(url) == url
