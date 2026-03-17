import base64

import pytest

from app.services.multimodal_service import MultimodalService, MultimodalValidationError


def _to_data_uri(raw: bytes, mime_type: str = "image/png") -> str:
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def test_validate_images_rejects_too_large():
    service = MultimodalService(max_image_count=5, max_image_size_mb=1)
    oversized = _to_data_uri(b"a" * (1024 * 1024 + 1))

    with pytest.raises(MultimodalValidationError) as exc_info:
        service.validate_images([oversized])

    assert exc_info.value.code == "IMAGE_TOO_LARGE"


def test_validate_images_rejects_unsupported_mime():
    service = MultimodalService()
    invalid = _to_data_uri(b"abc", mime_type="application/pdf")

    with pytest.raises(MultimodalValidationError) as exc_info:
        service.validate_images([invalid])

    assert exc_info.value.code == "IMAGE_FORMAT_UNSUPPORTED"


@pytest.mark.parametrize(
    "model_capabilities,request_has_images,fallback_enabled,expected_supports,expected_enabled,expected_mode",
    [
        (["vision"], True, False, True, True, "none"),
        ([], True, False, False, False, "reject"),
        ([], True, True, False, False, "text_only"),
        (["vision"], False, False, True, False, "none"),
    ],
)
def test_decide_vision_enabled_matrix(
    model_capabilities,
    request_has_images,
    fallback_enabled,
    expected_supports,
    expected_enabled,
    expected_mode,
):
    service = MultimodalService()

    decision = service.decide_vision(
        model_capabilities=model_capabilities,
        request_has_images=request_has_images,
        fallback_enabled=fallback_enabled,
    )

    assert decision["supports_vision"] is expected_supports
    assert decision["vision_enabled"] is expected_enabled
    assert decision["fallback_mode"] == expected_mode
