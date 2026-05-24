from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "product_image_vectors.json"
DEFAULT_ENDPOINT = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/"
    "multimodal-embedding/multimodal-embedding"
)
REALTIME_MODELS = {"qwen3.5-omni-plus-realtime"}
DEFAULT_MAX_IMAGE_BYTES = 4_800_000
DEFAULT_IMAGE_MAX_SIDE = 1600
DATA_URL_RE = re.compile(r"^data:(?P<mime>image/[^;,]+);base64,(?P<data>.+)$", re.IGNORECASE | re.DOTALL)


@dataclass
class Product:
    id: int
    name: str | None
    price: Any
    stock: int | None
    category: str | None
    description: str | None
    image: str | None
    barcode: str | None
    status: int | None
    create_time: Any = None
    update_time: Any = None


FIELD_CANDIDATES = {
    "id": ("id",),
    "name": ("name",),
    "price": ("price",),
    "stock": ("stock",),
    "category": ("category",),
    "description": ("description",),
    "image": ("image",),
    "barcode": ("barcode",),
    "status": ("status",),
    "create_time": ("create_time", "createTime"),
    "update_time": ("update_time", "updateTime"),
}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got: {value}") from exc


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a number, got: {value}") from exc


def parse_args() -> argparse.Namespace:
    image_root = os.getenv("PRODUCT_IMAGE_ROOT")
    parser = argparse.ArgumentParser(
        description=(
            "Build fused multimodal product vectors from MySQL product images "
            "and product metadata."
        )
    )
    parser.add_argument("--api-key-env", default="DASHSCOPE_API_KEY")
    parser.add_argument("--endpoint", default=os.getenv("DASHSCOPE_MULTIMODAL_EMBEDDING_URL", DEFAULT_ENDPOINT))
    parser.add_argument("--model", default=os.getenv("PRODUCT_VECTOR_MODEL", "qwen3-vl-embedding"))
    parser.add_argument("--dimension", type=int, default=env_int("PRODUCT_VECTOR_DIMENSION", 1024))
    parser.add_argument("--output", type=Path, default=Path(os.getenv("PRODUCT_VECTOR_OUTPUT", DEFAULT_OUTPUT)))
    parser.add_argument("--image-root", type=Path, default=Path(image_root) if image_root else None)
    parser.add_argument("--include-inactive", action="store_true")
    parser.add_argument("--include-missing-image", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--request-interval", type=float, default=0.0)
    parser.add_argument("--max-image-bytes", type=int, default=env_int("PRODUCT_VECTOR_MAX_IMAGE_BYTES", DEFAULT_MAX_IMAGE_BYTES))
    parser.add_argument("--image-max-side", type=int, default=env_int("PRODUCT_VECTOR_IMAGE_MAX_SIDE", DEFAULT_IMAGE_MAX_SIDE))
    parser.add_argument("--image-timeout", type=float, default=env_float("PRODUCT_VECTOR_IMAGE_TIMEOUT", 30.0))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")

    parser.add_argument("--db-host", default=os.getenv("PRODUCT_DB_HOST", "localhost"))
    parser.add_argument("--db-port", type=int, default=env_int("PRODUCT_DB_PORT", 3306))
    parser.add_argument("--db-name", default=os.getenv("PRODUCT_DB_NAME", "unmanned_supermarket"))
    parser.add_argument("--db-user", default=os.getenv("PRODUCT_DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("PRODUCT_DB_PASSWORD", "123456"))
    parser.add_argument("--db-table", default=os.getenv("PRODUCT_DB_TABLE", "product"))
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.model in REALTIME_MODELS:
        raise SystemExit(
            f"{args.model} is a realtime conversation model, not an embedding model. "
            "Use qwen3-vl-embedding or another multimodal embedding model instead."
        )
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.db_table):
        raise SystemExit(f"Unsafe table name: {args.db_table}")
    if args.dimension <= 0:
        raise SystemExit("--dimension must be greater than 0")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be greater than 0")
    if args.max_image_bytes <= 0:
        raise SystemExit("--max-image-bytes must be greater than 0")
    if args.image_max_side <= 0:
        raise SystemExit("--image-max-side must be greater than 0")


def connect_mysql(args: argparse.Namespace):
    try:
        import pymysql
        import pymysql.cursors
    except ImportError as exc:
        raise SystemExit("Missing pymysql. Run: .\\.venv\\Scripts\\pip.exe install -r requirements.txt") from exc

    return pymysql.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def load_columns(connection: Any, table: str) -> dict[str, str]:
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        rows = cursor.fetchall()
    return {row["Field"].lower(): row["Field"] for row in rows}


def pick_column(columns: dict[str, str], *names: str) -> str | None:
    for name in names:
        found = columns.get(name.lower())
        if found:
            return found
    return None


def build_select_parts(columns: dict[str, str]) -> tuple[list[str], dict[str, str | None]]:
    selected: list[str] = []
    column_map: dict[str, str | None] = {}
    for alias, candidates in FIELD_CANDIDATES.items():
        column = pick_column(columns, *candidates)
        column_map[alias] = column
        if column:
            selected.append(f"`{column}` AS `{alias}`")
        else:
            selected.append(f"NULL AS `{alias}`")
    return selected, column_map


def fetch_products(args: argparse.Namespace) -> list[Product]:
    connection = connect_mysql(args)
    try:
        columns = load_columns(connection, args.db_table)
        required = ["id", "image"]
        missing = [field for field in required if not pick_column(columns, *FIELD_CANDIDATES[field])]
        if missing:
            raise SystemExit(f"Table `{args.db_table}` is missing required columns: {', '.join(missing)}")

        select_parts, column_map = build_select_parts(columns)
        where: list[str] = []
        params: list[Any] = []
        status_col = column_map["status"]
        image_col = column_map["image"]

        if status_col and not args.include_inactive:
            where.append(f"`{status_col}` = %s")
            params.append(1)
        if image_col and not args.include_missing_image:
            where.append(f"`{image_col}` IS NOT NULL AND TRIM(`{image_col}`) <> ''")

        sql = f"SELECT {', '.join(select_parts)} FROM `{args.db_table}`"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY `id`"
        if args.limit:
            sql += " LIMIT %s"
            params.append(args.limit)

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    finally:
        connection.close()

    return [Product(**row) for row in rows]


def stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def product_text(product: Product) -> str:
    parts = [
        ("Product name", product.name),
        ("Category", product.category),
        ("Description", product.description),
        ("Barcode", product.barcode),
        ("Price", stringify(product.price)),
        ("Image URL or path", product.image),
    ]
    return "\n".join(f"{label}: {value}" for label, value in parts if stringify(value))


def is_remote_image(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("http://") or lower.startswith("https://") or lower.startswith("data:image/")


def data_url_to_bytes(value: str) -> tuple[bytes, str] | None:
    match = DATA_URL_RE.match(value)
    if not match:
        return None
    return base64.b64decode(match.group("data")), match.group("mime").lower()


def guess_image_mime(source_name: str | None, data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"

    mime_type, _ = mimetypes.guess_type(source_name or "")
    if mime_type and mime_type.startswith("image/"):
        return mime_type
    return "image/jpeg"


def image_to_data_url(data: bytes, mime_type: str) -> str:
    data = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{data}"


def read_image_bytes(image: str | None, image_root: Path | None, timeout: float) -> tuple[bytes | None, str | None, str | None]:
    if not image:
        return None, None, "missing image"

    image = image.strip()
    data_url = data_url_to_bytes(image)
    if data_url:
        data, mime_type = data_url
        return data, mime_type, None

    if image.lower().startswith(("http://", "https://")):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(image)
            response.raise_for_status()
        except Exception as exc:
            return None, None, f"cannot download image: {exc}"

        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        mime_type = content_type if content_type.startswith("image/") else guess_image_mime(image, response.content)
        return response.content, mime_type, None

    candidates = [Path(image)]
    if image_root:
        candidates.append(image_root / image.lstrip("/\\"))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            data = candidate.read_bytes()
            return data, guess_image_mime(candidate.name, data), None

    return None, None, f"image is not a URL and cannot be found locally: {image}"


def compress_image_bytes(data: bytes, max_bytes: int, max_side: int) -> tuple[bytes, str]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("image is too large and Pillow is missing; run pip install -r requirements.txt") from exc

    with Image.open(BytesIO(data)) as opened:
        image = ImageOps.exif_transpose(opened)
        if "A" in image.getbands():
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image.convert("RGB"), mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")

    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), resample)

    qualities = (90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40)
    while min(image.size) >= 240:
        for quality in qualities:
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
            output = buffer.getvalue()
            if len(output) <= max_bytes:
                return output, "image/jpeg"

        next_size = (max(240, int(image.width * 0.82)), max(240, int(image.height * 0.82)))
        if next_size == image.size:
            break
        image = image.resize(next_size, resample)

    raise RuntimeError(f"cannot compress image below {max_bytes} bytes")


def prepare_image_input(
    image: str | None,
    image_root: Path | None,
    max_bytes: int,
    max_side: int,
    timeout: float,
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    data, mime_type, error = read_image_bytes(image, image_root, timeout)
    if error:
        return None, None, error
    if data is None or mime_type is None:
        return None, None, "missing image data"

    original_bytes = len(data)
    normalized = False
    if original_bytes > max_bytes:
        data, mime_type = compress_image_bytes(data, max_bytes, max_side)
        normalized = True

    if len(data) > max_bytes:
        return None, None, f"prepared image is still too large: {len(data)} bytes"

    return image_to_data_url(data, mime_type), {
        "originalBytes": original_bytes,
        "preparedBytes": len(data),
        "mimeType": mime_type,
        "normalized": normalized,
    }, None


def build_payload(args: argparse.Namespace, text: str, image_input: str) -> dict[str, Any]:
    parameters: dict[str, Any] = {"dimension": args.dimension}
    if args.model == "qwen3-vl-embedding":
        parameters["enable_fusion"] = True

    return {
        "model": args.model,
        "input": {
            "contents": [
                {"text": text},
                {"image": image_input},
            ]
        },
        "parameters": parameters,
    }


def call_embedding(args: argparse.Namespace, api_key: str, text: str, image_input: str) -> dict[str, Any]:
    payload = build_payload(args, text, image_input)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(args.endpoint, headers=headers, json=payload)

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"DashScope returned non-JSON response: {response.text[:300]}") from exc

    if response.status_code >= 400 or data.get("code"):
        code = data.get("code", response.status_code)
        message = data.get("message", response.text[:300])
        raise RuntimeError(f"DashScope error {code}: {message}")

    embeddings = data.get("output", {}).get("embeddings") or []
    if not embeddings:
        raise RuntimeError(f"DashScope response has no embeddings: {json.dumps(data, ensure_ascii=False)[:500]}")

    embedding_item = next(
        (item for item in embeddings if item.get("type") in {"fusion", "fused"}),
        embeddings[0],
    )
    return {
        "embedding": embedding_item.get("embedding"),
        "embeddingType": embedding_item.get("type"),
        "requestId": data.get("request_id"),
        "usage": data.get("usage"),
    }


def build_vectors(args: argparse.Namespace) -> dict[str, Any]:
    api_key = os.getenv(args.api_key_env)
    if not api_key and not args.dry_run:
        raise SystemExit(f"Environment variable {args.api_key_env} is not set")

    products = fetch_products(args)
    print(f"Loaded {len(products)} products from {args.db_name}.{args.db_table}")

    existing_items: list[dict[str, Any]] = []
    if args.resume and not args.dry_run and args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("model") != args.model or existing.get("dimension") != args.dimension:
            raise SystemExit("Existing vector file uses a different model or dimension; rerun without --resume")

        existing_items = existing.get("items") or []
        existing_ids = {
            int(item["productId"])
            for item in existing_items
            if isinstance(item, dict) and item.get("productId") is not None
        }
        if existing_ids:
            products = [product for product in products if product.id not in existing_ids]
            print(f"Resume mode: keeping {len(existing_items)} existing vectors, building {len(products)} missing vectors")

    items: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    ready_count = 0

    for index, product in enumerate(products, start=1):
        text = product_text(product)
        image_input, image_meta, skip_reason = prepare_image_input(
            product.image,
            args.image_root,
            args.max_image_bytes,
            args.image_max_side,
            args.image_timeout,
        )
        if skip_reason:
            skipped.append({"productId": product.id, "name": product.name, "reason": skip_reason})
            print(f"[{index}/{len(products)}] skip product {product.id}: {skip_reason}")
            continue

        ready_count += 1
        if args.dry_run:
            size_info = ""
            if image_meta:
                size_info = f" ({image_meta['originalBytes']} -> {image_meta['preparedBytes']} bytes)"
            print(f"[{index}/{len(products)}] ready product {product.id}: {product.name}{size_info}")
            continue

        assert api_key is not None
        print(f"[{index}/{len(products)}] embedding product {product.id}: {product.name}")
        try:
            embedding_result = call_embedding(args, api_key, text, image_input)
        except Exception as exc:
            skipped.append({"productId": product.id, "name": product.name, "reason": str(exc)})
            print(f"[{index}/{len(products)}] failed product {product.id}: {exc}", file=sys.stderr)
            continue

        items.append(
            {
                "productId": product.id,
                "name": product.name,
                "category": product.category,
                "description": product.description,
                "barcode": product.barcode,
                "price": stringify(product.price),
                "stock": product.stock,
                "status": product.status,
                "image": product.image,
                "imageMeta": image_meta,
                "createTime": stringify(product.create_time),
                "updateTime": stringify(product.update_time),
                "text": text,
                **embedding_result,
            }
        )

        if args.request_interval > 0:
            time.sleep(args.request_interval)

    merged_items = existing_items + items
    merged_items.sort(key=lambda item: int(item.get("productId", 0)))

    return {
        "model": args.model,
        "dimension": args.dimension,
        "vectorMode": "fusion",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "database": args.db_name,
            "table": args.db_table,
            "imageRoot": str(args.image_root) if args.image_root else None,
        },
        "count": len(merged_items),
        "readyCount": len(existing_items) + ready_count,
        "skippedCount": len(skipped),
        "items": merged_items,
        "skipped": skipped,
    }


def main() -> None:
    args = parse_args()
    validate_args(args)
    result = build_vectors(args)

    if args.dry_run:
        print(f"Dry run complete. Ready: {result['readyCount']}, skipped: {result['skippedCount']}")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {result['count']} vectors to {args.output}")
    if result["skippedCount"]:
        print(f"Skipped {result['skippedCount']} products. See `skipped` in the output JSON.")


if __name__ == "__main__":
    main()
