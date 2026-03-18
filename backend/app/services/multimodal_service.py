import base64
from typing import Any, Dict, List, Optional
from pydantic_ai.messages import ImageUrl


class MultimodalValidationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class MultimodalService:
    def __init__(
        self,
        max_image_count: int = 10,
        max_image_size_mb: int = 10,
        allowed_mime_types: Optional[List[str]] = None,
    ):
        self.max_image_count = max_image_count
        self.max_image_size_bytes = max_image_size_mb * 1024 * 1024
        self.allowed_mime_types = allowed_mime_types or [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp",
            "image/gif",
        ]

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "MultimodalService":
        multimodal_cfg = config.get("multimodal", {}) if isinstance(config, dict) else {}
        return cls(
            max_image_count=int(multimodal_cfg.get("max_image_count", 10)),
            max_image_size_mb=int(multimodal_cfg.get("max_image_size_mb", 10)),
            allowed_mime_types=list(
                multimodal_cfg.get(
                    "allowed_mime_types",
                    ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"],
                )
            ),
        )

    def normalize_images(self, images: Optional[List[str]]) -> List[str]:
        if not images:
            return []
        if not isinstance(images, list):
            raise MultimodalValidationError("IMAGE_PAYLOAD_INVALID", "images_must_be_list")
        normalized = []
        for item in images:
            if not isinstance(item, str):
                continue
            value = item.strip()
            if value:
                normalized.append(value)
        return normalized

    def validate_images(self, images: Optional[List[str]]) -> List[str]:
        normalized = self.normalize_images(images)
        if not normalized:
            return []
        if len(normalized) > self.max_image_count:
            raise MultimodalValidationError("IMAGE_TOO_MANY", "too_many_images")
        for image in normalized:
            self._validate_single_image(image)
        return normalized

    def decide_vision(
        self,
        model_capabilities: Optional[List[str]],
        request_has_images: bool,
        fallback_enabled: bool,
    ) -> Dict[str, Any]:
        supports_vision = "vision" in (model_capabilities or [])
        vision_enabled = bool(supports_vision and request_has_images)
        fallback_mode = "none"
        if request_has_images and not supports_vision:
            fallback_mode = "text_only" if fallback_enabled else "reject"
        return {
            "supports_vision": supports_vision,
            "vision_enabled": vision_enabled,
            "fallback_mode": fallback_mode,
        }

    def build_user_input(
        self,
        message: Optional[str],
        validated_images: Optional[List[str]],
        vision_enabled: bool,
    ) -> str | List[Any]:
        text = (message or "").strip()
        if not vision_enabled:
            return text
        parts: List[Any] = []
        if text:
            parts.append(text)
        for image in validated_images or []:
            parts.append(ImageUrl(url=image))
        return parts if parts else text

    def _validate_single_image(self, image: str) -> None:
        if image.startswith("/files/"):
            return
        mime_type = "image/png"
        encoded = image
        if image.startswith("data:"):
            if "," not in image:
                raise MultimodalValidationError("IMAGE_DECODE_FAILED", "invalid_data_uri")
            header, encoded = image.split(",", 1)
            mime_type = header.replace("data:", "").split(";")[0].lower()
            if mime_type not in self.allowed_mime_types:
                raise MultimodalValidationError("IMAGE_FORMAT_UNSUPPORTED", "unsupported_mime_type")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise MultimodalValidationError("IMAGE_DECODE_FAILED", "invalid_base64_image") from exc
        if len(decoded) > self.max_image_size_bytes:
            raise MultimodalValidationError("IMAGE_TOO_LARGE", "image_too_large")
