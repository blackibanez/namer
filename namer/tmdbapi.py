"""
Helpers to query TMDb and map results into LookedUpFileInfo.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import orjson
from loguru import logger

from namer.comparison_results import LookedUpFileInfo, Performer, SceneType
from namer.configuration import NamerConfig
from namer.fileinfo import FileInfo
from namer.http import Http

TMDB_API_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_SITE_BASE_URL = 'https://www.themoviedb.org'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p'
TMDB_UUID_PREFIX = 'tmdb/movie/'


def is_tmdb_enabled(config: NamerConfig) -> bool:
    return bool(config.themoviedb_api_key and config.themoviedb_api_key.strip())


def is_tmdb_uuid(uuid: Optional[str]) -> bool:
    return bool(uuid and uuid.startswith(TMDB_UUID_PREFIX))


def _tmdb_headers() -> Dict[str, str]:
    return {
        'Accept': 'application/json',
        'User-Agent': 'namer-1',
    }


def _tmdb_url(path: str, config: NamerConfig, **params: Any) -> str:
    query = {
        'api_key': config.themoviedb_api_key,
        **params,
    }
    return f'{TMDB_API_BASE_URL}{path}?{urlencode(query)}'


def _build_image_url(path: Optional[str], size: str = 'w500') -> Optional[str]:
    if not path:
        return None

    return f'{TMDB_IMAGE_BASE_URL}/{size}{path}'


def _build_site_url(movie_id: int) -> str:
    return f'{TMDB_SITE_BASE_URL}/movie/{movie_id}'


def _parse_tmdb_movie(movie: Dict[str, Any], details: Dict[str, Any], query_url: str, name_parts: Optional[FileInfo]) -> LookedUpFileInfo:
    file_info = LookedUpFileInfo()

    movie_id = details.get('id', movie.get('id'))
    title = details.get('title', movie.get('title'))
    release_date = details.get('release_date', movie.get('release_date'))
    runtime = details.get('runtime')
    if runtime:
        runtime *= 60

    file_info.uuid = f'{TMDB_UUID_PREFIX}{movie_id}'
    file_info.guid = str(movie_id) if movie_id is not None else None
    file_info.external_id = str(movie_id) if movie_id is not None else None
    file_info.look_up_site_id = str(movie_id) if movie_id is not None else None
    file_info.type = SceneType.MOVIE
    file_info.name = title
    file_info.description = details.get('overview', movie.get('overview'))
    file_info.date = release_date
    file_info.site = 'TMDb'
    file_info.parent = None
    file_info.network = None
    file_info.source_url = _build_site_url(movie_id) if movie_id is not None else None
    file_info.poster_url = _build_image_url(details.get('poster_path', movie.get('poster_path')))
    file_info.background_url = _build_image_url(details.get('backdrop_path', movie.get('backdrop_path')), size='original')
    file_info.duration = runtime
    file_info.tags = [genre['name'] for genre in details.get('genres', []) if genre.get('name')]

    credits = details.get('credits', {})
    cast = credits.get('cast', [])
    for cast_member in cast[:10]:
        name = cast_member.get('name')
        if not name:
            continue

        performer = Performer(name, role=cast_member.get('character'))
        performer.alias = cast_member.get('original_name')
        performer.image = _build_image_url(cast_member.get('profile_path'))
        file_info.performers.append(performer)

    file_info.original_query = query_url
    file_info.original_response = orjson.dumps(details, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode('UTF-8')
    file_info.original_parsed_filename = name_parts if name_parts else FileInfo()

    return file_info


def _request_tmdb_json(url: str) -> Optional[Dict[str, Any]]:
    response = Http.get(url, headers=_tmdb_headers())
    if not response.ok:
        logger.error('TMDb API error: {} {}', response.status_code, url)
        return None

    return response.json()


def search_movies(query: str, config: NamerConfig, page: int = 1, name_parts: Optional[FileInfo] = None) -> List[LookedUpFileInfo]:
    if not is_tmdb_enabled(config) or not query.strip():
        return []

    search_url = _tmdb_url('/search/movie', config, query=query, page=page, include_adult='true')
    payload = _request_tmdb_json(search_url)
    if not payload:
        return []

    results: List[LookedUpFileInfo] = []
    for movie in payload.get('results', [])[:25]:
        movie_id = movie.get('id')
        if movie_id is None:
            continue

        details = get_movie_details(f'{TMDB_UUID_PREFIX}{movie_id}', config)
        if details:
            details.original_query = search_url
            if name_parts:
                details.original_parsed_filename = name_parts
            results.append(details)

    return results


def get_movie_details(uuid: str, config: NamerConfig, name_parts: Optional[FileInfo] = None) -> Optional[LookedUpFileInfo]:
    if not is_tmdb_enabled(config) or not is_tmdb_uuid(uuid):
        return None

    movie_id = uuid.removeprefix(TMDB_UUID_PREFIX)
    details_url = _tmdb_url(f'/movie/{movie_id}', config, append_to_response='credits')
    payload = _request_tmdb_json(details_url)
    if not payload:
        return None

    return _parse_tmdb_movie(payload, payload, details_url, name_parts)
