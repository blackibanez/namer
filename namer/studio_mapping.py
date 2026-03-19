import re
from pathlib import Path
from typing import Dict, Optional

import orjson
from loguru import logger

from namer.configuration import NamerConfig


def _normalize_studio_key(studio: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', studio.lower()).strip()


def _resolve_mapping_file(config: NamerConfig) -> Optional[Path]:
    mapping_file = getattr(config, 'studio_mappings_file', None)
    if not mapping_file:
        return None

    path = Path(mapping_file)
    if path.is_absolute():
        return path

    explicit_path = path.resolve()
    if path.parent != Path('.') and explicit_path.is_file():
        return explicit_path

    config_file = getattr(config, 'config_file', None)
    if config_file:
        config_relative_path = (config_file.parent / path).resolve()
        if config_relative_path.is_file():
            return config_relative_path

    return explicit_path


def load_studio_mappings(config: NamerConfig) -> Dict[str, str]:
    path = _resolve_mapping_file(config)
    mappings: Dict[str, str] = {}

    if not path or not path.is_file():
        config.studio_mappings = mappings
        return mappings

    try:
        payload = orjson.loads(path.read_bytes())
    except orjson.JSONDecodeError:
        logger.error('Invalid studio mapping file: {}', path)
        config.studio_mappings = mappings
        return mappings

    if not isinstance(payload, dict):
        logger.error('Studio mapping file must contain a JSON object: {}', path)
        config.studio_mappings = mappings
        return mappings

    for source_name, target_name in payload.items():
        if not isinstance(source_name, str) or not isinstance(target_name, str):
            continue

        normalized_source = _normalize_studio_key(source_name)
        normalized_target = target_name.strip()
        if normalized_source and normalized_target:
            mappings[normalized_source] = normalized_target

    config.studio_mappings = mappings
    return mappings


def normalize_studio_name(studio: Optional[str], config: NamerConfig) -> Optional[str]:
    if not studio:
        return studio

    mappings = getattr(config, 'studio_mappings', None)
    if mappings is None:
        mappings = load_studio_mappings(config)

    cleaned_studio = studio.strip()
    return mappings.get(_normalize_studio_key(cleaned_studio), cleaned_studio)
