import json
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import catalog


class CatalogTests(unittest.TestCase):
    def test_complete_current_country_catalogue(self):
        source = json.loads((catalog.ROOT / 'countries.json').read_text(encoding='utf-8'))
        expected = {country['code'] for country in source} - {'AN', 'CS'}
        self.assertEqual(set(catalog.COUNTRY_MAP), expected)
        self.assertEqual(sum(country['cityCount'] for country in catalog.COUNTRIES), len(catalog.CITIES))
        for code in ('AQ', 'BV', 'HM', 'IO', 'TK', 'UM'):
            self.assertIn(code, catalog.COUNTRY_MAP)
            self.assertEqual(catalog.COUNTRY_MAP[code]['cityCount'], 0)
    def test_every_current_country_has_a_local_photo_with_attribution(self):
        for country in catalog.COUNTRIES:
            with self.subTest(code=country['code']):
                photo = catalog.COUNTRY_PHOTOS[country['code']]
                self.assertEqual(photo['photo'], '/assets-country/'+country['code'].lower()+'.jpg')
                self.assertTrue((catalog.ROOT / photo['photo'].lstrip('/')).read_bytes().startswith(b'\xff\xd8'))
                self.assertTrue(photo['photoSource'].startswith('https://'))
                self.assertTrue(photo['author'].strip())
                self.assertTrue(photo['license'].strip())

    def test_empty_territory_and_empty_search_reset_pagination(self):
        for query in ('country=AQ&page=99', 'q=zzzzno-such-placezzzz&page=9', 'country=ZZ&page=5'):
            with self.subTest(query=query):
                result = catalog.search(query)
                self.assertEqual((result['items'], result['total'], result['page'], result['pages']), ([], 0, 1, 1))
                self.assertEqual(result['countryCount'], len(catalog.COUNTRIES))

    def test_out_of_range_page_clamps_to_last_real_page(self):
        result = catalog.search('country=FR&page=999999')
        last_page = catalog.search('country=FR&page=' + str(result['pages']))
        self.assertEqual(result['items'], last_page['items'])
        self.assertEqual(result['page'], result['pages'])
        self.assertTrue(0 < len(result['items']) <= catalog.PAGE_SIZE)

    def test_invalid_page_and_country_codes(self):
        for page in ('-100', '0', 'abc', '1.5', '9' * 5000):
            with self.subTest(page=page[:20]):
                result = catalog.search('country=FR&page=' + page)
                self.assertGreaterEqual(result['page'], 1)
                self.assertLessEqual(result['page'], result['pages'])
        self.assertEqual(catalog.search('country=fr')['total'], catalog.search('country=FR')['total'])
        self.assertEqual(catalog.search('country=FRANCE')['total'], 0)

    def test_names_aliases_and_russian_country_search(self):
        self.assertEqual(catalog.search('q=Paris&country=FR')['items'][0]['name'], 'Paris')
        french = catalog.search(urlencode({'q': 'Франция'}))
        self.assertGreater(french['total'], 0)
        self.assertTrue(all(city['code'] == 'FR' for city in french['items']))
        sao = catalog.search(urlencode({'q': 'sao paulo', 'country': 'BR'}))
        accented = catalog.search(urlencode({'q': 'São Paulo', 'country': 'BR'}))
        self.assertEqual(sao['items'], accented['items'])
        self.assertGreater(sao['total'], 0)

    def test_continent_filter_and_stable_sort(self):
        result = catalog.search('continent=EU&sort=population')
        self.assertTrue(all(city['continent'] == 'EU' for city in result['items']))
        populations = [city['population'] for city in result['items']]
        self.assertEqual(populations, sorted(populations, reverse=True))
        second = catalog.search('continent=EU&sort=population&page=2')
        self.assertTrue(set(city['id'] for city in result['items']).isdisjoint(city['id'] for city in second['items']))

    def test_country_photo_fallback_is_never_described_as_the_city(self):
        city = next(city for city in catalog.CITIES if city['id'] not in catalog.PHOTOS)
        fixture = {'photo': 'https://upload.wikimedia.org/example.jpg',
                   'photoSource': 'https://commons.wikimedia.org/wiki/File:Example.jpg',
                   'author': 'Example author', 'license': 'CC BY 4.0',
                   'guide': 'https://en.wikipedia.org/wiki/Some_country',
                   'description': 'A country, not this city'}
        with patch.dict(catalog.COUNTRY_PHOTOS, {city['code']: fixture}):
            result = catalog.destination(city)
        self.assertEqual(result['photoScope'], 'country')
        self.assertEqual(result['photoLabel'], catalog.COUNTRY_MAP[city['code']]['name'])
        self.assertEqual(result['photoSource'], fixture['photoSource'])
        self.assertEqual(result['author'], fixture['author'])
        self.assertNotIn('description', result)
        self.assertNotIn('guide', result)
        self.assertEqual(result['name'], city['name'])

    def test_city_photo_takes_precedence_and_estimates_are_explicit(self):
        city = next(city for city in catalog.CITIES if city['id'] in catalog.PHOTOS)
        with patch.dict(catalog.COUNTRY_PHOTOS, {city['code']: {'photo': 'country-photo'}}):
            result = catalog.destination(city)
        self.assertEqual(result['photo'], catalog.PHOTOS[city['id']]['photo'])
        self.assertEqual(result['photoScope'], 'city')
        self.assertEqual(result['photoLabel'], city['name'])
        self.assertTrue(result['budgetIsEstimate'])
        self.assertEqual(result['cost'], result['daily'] * result['days'])


if __name__ == '__main__':
    unittest.main()
