"""Tests for vision/image detection in proxy."""

from typing import Any, AsyncGenerator, Dict, List

import pytest

from config import Config, ControllerConfig, LLMConfig, MemoryConfig, ProxyConfig
from proxy import SekhaProxy


@pytest.fixture
def proxy_config() -> Config:
    """Create test configuration."""
    return Config(
        proxy=ProxyConfig(host="127.0.0.1", port=5000),
        llm=LLMConfig(
            bridge_url="http://mock-bridge:5001",
            preferred_chat_model="llama3.1:8b",
            preferred_vision_model="gpt-4o",
            timeout=120,
        ),
        controller=ControllerConfig(
            url="http://mock-controller:8080",
            api_key="test-key",
            timeout=30,
        ),
        memory=MemoryConfig(
            auto_inject_context=True,
            context_token_budget=4000,
            excluded_folders=[],
            default_folder="/test",
            preferred_labels=[],
        ),
    )


@pytest.fixture
async def proxy(proxy_config: Config) -> AsyncGenerator[SekhaProxy, None]:
    """Create proxy instance."""
    instance = SekhaProxy(proxy_config)
    yield instance
    await instance.close()


class TestVisionDetection:
    """Tests for image/vision detection in messages."""

    @pytest.mark.asyncio
    async def test_detect_openai_multimodal_format(self, proxy: SekhaProxy):
        """Test detection of OpenAI multimodal format (content as list with image_url)."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/image.jpg"},
                    },
                ],
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 1

    @pytest.mark.asyncio
    async def test_detect_multiple_images_multimodal(self, proxy: SekhaProxy):
        """Test detection of multiple images in multimodal format."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Compare these images:"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/image1.jpg"},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/image2.png"},
                    },
                ],
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 2

    @pytest.mark.asyncio
    async def test_detect_image_url_in_text_jpg(self, proxy: SekhaProxy):
        """Test detection of .jpg image URL in text content."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "Please analyze this image: https://example.com/photo.jpg",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 1

    @pytest.mark.asyncio
    async def test_detect_image_url_in_text_png(self, proxy: SekhaProxy):
        """Test detection of .png image URL in text content."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "Check out https://cdn.example.com/images/screenshot.png for reference",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 1

    @pytest.mark.asyncio
    async def test_detect_image_url_with_query_params(self, proxy: SekhaProxy):
        """Test detection of image URL with query parameters."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "See: https://example.com/image.jpg?size=large&format=hd#section",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 1

    @pytest.mark.asyncio
    async def test_detect_multiple_image_extensions(self, proxy: SekhaProxy):
        """Test detection of various image file extensions."""
        extensions = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg"]

        for ext in extensions:
            messages: List[Dict[str, Any]] = [
                {
                    "role": "user",
                    "content": f"Image at https://example.com/test.{ext}",
                }
            ]

            has_images, image_count = proxy._detect_images_in_messages(messages)

            assert has_images is True, f"Failed to detect .{ext} image"
            assert image_count == 1, f"Wrong count for .{ext} image"

    @pytest.mark.asyncio
    async def test_detect_case_insensitive_extensions(self, proxy: SekhaProxy):
        """Test that image detection is case-insensitive."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "Images: https://example.com/photo.JPG and https://example.com/pic.PNG",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 2

    @pytest.mark.asyncio
    async def test_detect_base64_data_uri(self, proxy: SekhaProxy):
        """Test detection of base64 data URI."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "Here's an embedded image: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA...",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 1

    @pytest.mark.asyncio
    async def test_detect_multiple_base64_images(self, proxy: SekhaProxy):
        """Test detection of multiple base64 data URIs."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    "First: data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA... "
                    "Second: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..."
                ),
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 2

    @pytest.mark.asyncio
    async def test_detect_mixed_formats(self, proxy: SekhaProxy):
        """Test detection when mixing different image formats."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Compare these:"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/photo1.jpg"},
                    },
                ],
            },
            {
                "role": "user",
                "content": "And also this URL: https://example.com/photo2.png",
            },
            {
                "role": "user",
                "content": "Plus embedded: data:image/gif;base64,R0lGODlhAQABAIA...",
            },
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 3  # One from each message

    @pytest.mark.asyncio
    async def test_detect_across_multiple_messages(self, proxy: SekhaProxy):
        """Test detection of images across multiple messages."""
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": "First image: https://example.com/a.jpg"},
            {"role": "assistant", "content": "I see the first image."},
            {"role": "user", "content": "Second image: https://example.com/b.png"},
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 2

    @pytest.mark.asyncio
    async def test_no_images_text_only(self, proxy: SekhaProxy):
        """Test that pure text messages return False."""
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is False
        assert image_count == 0

    @pytest.mark.asyncio
    async def test_no_images_empty_messages(self, proxy: SekhaProxy):
        """Test empty message list."""
        messages: List[Dict[str, Any]] = []

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is False
        assert image_count == 0

    @pytest.mark.asyncio
    async def test_no_images_missing_content(self, proxy: SekhaProxy):
        """Test messages with missing content field."""
        messages: List[Dict[str, Any]] = [
            {"role": "user"},  # No content field
            {"role": "assistant", "content": ""},  # Empty content
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is False
        assert image_count == 0

    @pytest.mark.asyncio
    async def test_false_positive_prevention_image_word(self, proxy: SekhaProxy):
        """Test that the word 'image' doesn't trigger false positives."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "Tell me about image processing without showing any images.",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is False
        assert image_count == 0

    @pytest.mark.asyncio
    async def test_false_positive_prevention_non_image_url(self, proxy: SekhaProxy):
        """Test that non-image URLs don't trigger detection."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "Check this website: https://example.com/page.html",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is False
        assert image_count == 0

    @pytest.mark.asyncio
    async def test_multimodal_format_with_non_image_items(self, proxy: SekhaProxy):
        """Test multimodal content with only text items (no images)."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "text", "text": "World"},
                ],
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is False
        assert image_count == 0

    @pytest.mark.asyncio
    async def test_http_and_https_urls(self, proxy: SekhaProxy):
        """Test detection of both HTTP and HTTPS image URLs."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "HTTP: http://example.com/image.jpg and HTTPS: https://secure.com/pic.png",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 2

    @pytest.mark.asyncio
    async def test_url_with_special_characters(self, proxy: SekhaProxy):
        """Test detection of image URLs with special characters in path."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": "Image: https://example.com/user/photos/vacation%202024/photo-001.jpg",
            }
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 1

    @pytest.mark.asyncio
    async def test_image_count_accuracy(self, proxy: SekhaProxy):
        """Test that image count is accurate for complex scenarios."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Multiple formats:"},
                    {  # Multimodal format
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/1.jpg"},
                    },
                    {  # Multimodal format
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/2.png"},
                    },
                ],
            },
            {
                "role": "user",
                "content": (
                    # URL in text
                    "URL images: https://example.com/3.gif and https://example.com/4.webp "
                    # Base64 in text
                    "Plus base64: data:image/jpeg;base64,AAAA data:image/png;base64,BBBB"
                ),
            },
        ]

        has_images, image_count = proxy._detect_images_in_messages(messages)

        assert has_images is True
        assert image_count == 6  # 2 multimodal + 2 URLs + 2 base64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
