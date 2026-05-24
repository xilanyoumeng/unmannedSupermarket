from __future__ import annotations

import base64
import json
import math
import mimetypes
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_VECTOR_PATH = PROJECT_ROOT / "data" / "product_image_vectors.json"
DEFAULT_ENDPOINT = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/"
    "multimodal-embedding/multimodal-embedding"
)
DEFAULT_MAX_IMAGE_BYTES = 4_800_000
DEFAULT_IMAGE_MAX_SIDE = 1600


class ProductVectorRecognizer:
    def __init__(self) -> None:
        self.vector_path = Path(os.getenv("PRODUCT_VECTOR_OUTPUT", DEFAULT_VECTOR_PATH))
        self.api_key_env = "DASHSCOPE_API_KEY"
        self.endpoint = os.getenv("DASHSCOPE_MULTIMODAL_EMBEDDING_URL", DEFAULT_ENDPOINT)
        self.max_image_bytes = int(os.getenv("PRODUCT_VECTOR_MAX_IMAGE_BYTES", str(DEFAULT_MAX_IMAGE_BYTES)))
        self.image_max_side = int(os.getenv("PRODUCT_VECTOR_IMAGE_MAX_SIDE", str(DEFAULT_IMAGE_MAX_SIDE)))
        self.timeout = float(os.getenv("PRODUCT_VECTOR_RECOGNIZE_TIMEOUT", "120"))
        self._mtime: float | None = None
        self._model = "qwen3-vl-embedding"
        self._dimension = 1024
        self._items: list[dict[str, Any]] = []

    def status(self) -> dict[str, Any]:
        self._load_vectors()
        return {
            "vectorPath": str(self.vector_path),
            "model": self._model,
            "dimension": self._dimension,
            "count": len(self._items),
        }

    def recognize(
        self,
        image_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        top_k: int = 5,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        resolved_api_key = api_key or os.getenv(self.api_key_env)
        if not resolved_api_key:
            raise RuntimeError(f"Environment variable {self.api_key_env} is not set")

        self._load_vectors()
        if not self._items:
            raise RuntimeError(f"No product vectors found in {self.vector_path}")

        mime_type = self._guess_mime(filename, content_type, image_bytes)
        prepared_bytes, prepared_mime, image_meta = self._prepare_image(image_bytes, mime_type)
        query_vector = self._embed_image(resolved_api_key, self._to_data_url(prepared_bytes, prepared_mime))

        ranked = []
        query_norm = self._norm(query_vector)
        for item in self._items:
            score = self._cosine(query_vector, query_norm, item["embedding"], item["norm"])
            ranked.append({
                "productId": item["productId"],
                "name": item.get("name"),
                "price": item.get("price"),
                "category": item.get("category"),
                "image": item.get("image"),
                "confidence": round(max(0.0, min(1.0, score)), 4),
                "score": round(score, 6),
            })

        ranked.sort(key=lambda item: item["score"], reverse=True)
        candidates = ranked[:max(1, top_k)]
        best = candidates[0]
        return {
            "productId": best["productId"],
            "name": best["name"],
            "price": float(best["price"] or 0),
            "confidence": best["confidence"],
            "image": best["image"],
            "needsConfirmation": best["confidence"] < 0.72,
            "candidates": candidates,
            "imageMeta": image_meta,
        }

    def _load_vectors(self) -> None:
        if not self.vector_path.exists():
            raise RuntimeError(f"Vector file not found: {self.vector_path}")

        mtime = self.vector_path.stat().st_mtime
        if self._mtime == mtime and self._items:
            return

        data = json.loads(self.vector_path.read_text(encoding="utf-8"))
        self._model = data.get("model") or "qwen3-vl-embedding"
        self._dimension = int(data.get("dimension") or 1024)
        items = []
        for raw in data.get("items") or []:
            embedding = raw.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                continue
            vector = [float(value) for value in embedding]
            items.append({
                "productId": int(raw["productId"]),
                "name": raw.get("name"),
                "price": raw.get("price"),
                "category": raw.get("category"),
                "image": raw.get("image"),
                "embedding": vector,
                "norm": self._norm(vector),
            })

        self._items = items
        self._mtime = mtime

    def _embed_image(self, api_key: str, image_data_url: str) -> list[float]:
        parameters: dict[str, Any] = {"dimension": self._dimension}
        if self._model == "qwen3-vl-embedding":
            parameters["enable_fusion"] = True

        payload = {
            "model": self._model,
            "input": {"contents": [{"image": image_data_url}]},
            "parameters": parameters,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.endpoint, headers=headers, json=payload)

        data = response.json()
        if response.status_code >= 400 or data.get("code"):
            code = data.get("code", response.status_code)
            message = data.get("message", response.text[:300])
            raise RuntimeError(f"DashScope error {code}: {message}")

        embeddings = data.get("output", {}).get("embeddings") or []
        if not embeddings:
            raise RuntimeError("DashScope response has no embeddings")

        embedding_item = next(
            (item for item in embeddings if item.get("type") in {"fusion", "fused", "vl", "image"}),
            embeddings[0],
        )
        return [float(value) for value in embedding_item["embedding"]]

    def _prepare_image(self, data: bytes, mime_type: str) -> tuple[bytes, str, dict[str, Any]]:
        original_bytes = len(data)
        normalized = False
        if original_bytes > self.max_image_bytes:
            data, mime_type = self._compress_image(data)
            normalized = True

        if len(data) > self.max_image_bytes:
            raise RuntimeError(f"Image is too large after compression: {len(data)} bytes")

        return data, mime_type, {
            "originalBytes": original_bytes,
            "preparedBytes": len(data),
            "mimeType": mime_type,
            "normalized": normalized,
        }

    def _compress_image(self, data: bytes) -> tuple[bytes, str]:
        with Image.open(BytesIO(data)) as opened:
            image = ImageOps.exif_transpose(opened)
            if "A" in image.getbands():
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image.convert("RGB"), mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        if max(image.size) > self.image_max_side:
            image.thumbnail((self.image_max_side, self.image_max_side), resample)

        for quality in (90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40):
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
            output = buffer.getvalue()
            if len(output) <= self.max_image_bytes:
                return output, "image/jpeg"

        raise RuntimeError(f"Cannot compress image below {self.max_image_bytes} bytes")

    @staticmethod
    def _guess_mime(filename: str | None, content_type: str | None, data: bytes) -> str:
        if content_type and content_type.startswith("image/"):
            return content_type
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        mime_type, _ = mimetypes.guess_type(filename or "")
        return mime_type if mime_type and mime_type.startswith("image/") else "image/jpeg"

    @staticmethod
    def _to_data_url(data: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    @staticmethod
    def _norm(vector: list[float]) -> float:
        return math.sqrt(sum(value * value for value in vector)) or 1.0

    @staticmethod
    def _cosine(a: list[float], a_norm: float, b: list[float], b_norm: float) -> float:
        length = min(len(a), len(b))
        if length == 0:
            return 0.0
        dot = sum(a[index] * b[index] for index in range(length))
        return dot / (a_norm * b_norm)
