import unittest
from unittest import mock

from namer.metadataapi import get_complete_metadataapi_net_fileinfo
from namer.web.actions import SearchType, get_search_results
from test.utils import sample_config


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.ok = status_code < 400
        self.status_code = status_code

    def json(self):
        return self._payload


class UnitTestTMDb(unittest.TestCase):
    def setUp(self):
        self.config = sample_config()
        self.config.themoviedb_api_key = 'tmdb-test-key'

    @mock.patch('namer.tmdbapi.Http.get')
    def test_web_search_results_include_tmdb_movies(self, mock_get):
        search_payload = {
            'results': [
                {
                    'id': 603,
                    'title': 'The Matrix',
                    'overview': 'A computer hacker learns the truth.',
                    'release_date': '1999-03-30',
                    'poster_path': '/matrix.jpg',
                    'backdrop_path': '/matrix-bg.jpg',
                }
            ]
        }
        detail_payload = {
            'id': 603,
            'title': 'The Matrix',
            'overview': 'A computer hacker learns the truth.',
            'release_date': '1999-03-30',
            'poster_path': '/matrix.jpg',
            'backdrop_path': '/matrix-bg.jpg',
            'runtime': 136,
            'genres': [{'id': 878, 'name': 'Science Fiction'}],
            'credits': {
                'cast': [
                    {
                        'name': 'Keanu Reeves',
                        'original_name': 'Keanu Reeves',
                        'character': 'Neo',
                        'profile_path': '/neo.jpg',
                    }
                ]
            },
        }

        mock_get.side_effect = [
            FakeResponse(search_payload),
            FakeResponse(detail_payload),
        ]

        result = get_search_results('The Matrix', SearchType.TMDB, 'The.Matrix.1999.mkv', self.config)

        self.assertEqual(len(result['files']), 1)
        looked_up = result['files'][0]['looked_up']
        self.assertEqual(looked_up['uuid'], 'tmdb/movie/603')
        self.assertEqual(looked_up['name'], 'The Matrix')
        self.assertEqual(looked_up['site'], 'TMDb')
        self.assertEqual(looked_up['date'], '1999-03-30')
        self.assertEqual(looked_up['source_url'], 'https://www.themoviedb.org/movie/603')

    @mock.patch('namer.tmdbapi.Http.get')
    def test_complete_lookup_supports_tmdb_uuid(self, mock_get):
        detail_payload = {
            'id': 603,
            'title': 'The Matrix',
            'overview': 'A computer hacker learns the truth.',
            'release_date': '1999-03-30',
            'poster_path': '/matrix.jpg',
            'backdrop_path': '/matrix-bg.jpg',
            'runtime': 136,
            'genres': [{'id': 878, 'name': 'Science Fiction'}],
            'credits': {'cast': []},
        }
        mock_get.return_value = FakeResponse(detail_payload)

        result = get_complete_metadataapi_net_fileinfo(None, 'tmdb/movie/603', self.config)

        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.uuid, 'tmdb/movie/603')
            self.assertEqual(result.type.value, 'Movie')
            self.assertEqual(result.name, 'The Matrix')
            self.assertEqual(result.source_url, 'https://www.themoviedb.org/movie/603')
            self.assertEqual(result.duration, 8160)


if __name__ == '__main__':
    unittest.main()
