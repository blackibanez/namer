import tempfile
import unittest
from pathlib import Path

from namer import metadataapi
from namer.fileinfo import FileInfo
from namer.tmdbapi import _parse_tmdb_movie
from namer.studio_mapping import load_studio_mappings, normalize_studio_name
from test.utils import sample_config


class UnitTestStudioMappings(unittest.TestCase):
    def test_normalize_studio_name_from_mapping_file(self):
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            config = sample_config()
            config.config_file = Path(tmpdir) / '.namer.cfg'
            config.studio_mappings_file = 'studio_mappings.json'
            (Path(tmpdir) / 'studio_mappings.json').write_text(
                '{"warner":"Warner Bros.","Warner B.":"Warner Bros.","Warner Bros Production":"Warner Bros."}',
                encoding='UTF-8',
            )

            load_studio_mappings(config)

            self.assertEqual(normalize_studio_name('Warner', config), 'Warner Bros.')
            self.assertEqual(normalize_studio_name('Warner B.', config), 'Warner Bros.')
            self.assertEqual(normalize_studio_name('Warner Bros Production', config), 'Warner Bros.')
            self.assertEqual(normalize_studio_name('MGM', config), 'MGM')

    def test_tpdb_studio_mapping_is_applied(self):
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            config = sample_config()
            config.config_file = Path(tmpdir) / '.namer.cfg'
            config.studio_mappings_file = 'studio_mappings.json'
            (Path(tmpdir) / 'studio_mappings.json').write_text('{"Warner B.":"Warner Bros."}', encoding='UTF-8')
            load_studio_mappings(config)

            lookup = getattr(metadataapi, '__json_to_fileinfo')(
                {
                    '_id': '123',
                    'id': 'guid-123',
                    'type': 'movie',
                    'title': 'Example Movie',
                    'description': 'Example Description',
                    'date': '2024-01-01',
                    'url': 'https://example.test/movie/123',
                    'site': {'id': 1, 'parent_id': None, 'network_id': None, 'name': 'Warner B.'},
                    'performers': [],
                },
                'https://example.test/movies/123',
                '{}',
                FileInfo(),
                config,
            )

            self.assertEqual(lookup.site, 'Warner Bros.')

    def test_tmdb_studio_mapping_is_applied(self):
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            config = sample_config()
            config.config_file = Path(tmpdir) / '.namer.cfg'
            config.studio_mappings_file = 'studio_mappings.json'
            (Path(tmpdir) / 'studio_mappings.json').write_text('{"Warner Bros Production":"Warner Bros."}', encoding='UTF-8')
            load_studio_mappings(config)

            lookup = _parse_tmdb_movie(
                {'id': 603, 'title': 'The Matrix', 'adult': True},
                {
                    'id': 603,
                    'title': 'The Matrix',
                    'release_date': '1999-03-30',
                    'production_companies': [{'id': 999, 'name': 'Warner Bros Production'}],
                    'credits': {'cast': []},
                },
                'https://api.themoviedb.org/3/movie/603',
                config,
                None,
            )

            self.assertEqual(lookup.site, 'Warner Bros.')


if __name__ == '__main__':
    unittest.main()
