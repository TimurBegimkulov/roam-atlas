"""Offline GeoNames catalogue, with consistent country coverage in every search."""
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import unicodedata
from urllib.parse import parse_qs

ROOT = Path(__file__).parent
PAGE_SIZE = 24
# GeoNames countryInfo retains these retired codes for historical compatibility.
RETIRED_CODES = {'AN', 'CS'}
with gzip.open(ROOT / 'cities.json.gz', 'rt', encoding='utf-8') as stream:
    CITIES = json.load(stream)
COUNTRY_CITY_COUNTS = Counter(city['code'] for city in CITIES)
COUNTRY_CODES = set(COUNTRY_CITY_COUNTS)
COUNTRIES = [dict(country, cityCount=COUNTRY_CITY_COUNTS[country['code']])
             for country in json.loads((ROOT / 'countries.json').read_text(encoding='utf-8'))
             if country['code'] not in RETIRED_CODES]
COUNTRY_MAP = {country['code']: country for country in COUNTRIES}
PHOTOS = json.loads((ROOT / 'photos.json').read_text(encoding='utf-8'))
country_photo_path = ROOT / 'country-photos.json'
COUNTRY_PHOTOS = (json.loads(country_photo_path.read_text(encoding='utf-8'))
                  if country_photo_path.exists() else {})
BY_ID = {city['id']: city for city in CITIES}
BY_COUNTRY = defaultdict(list)
for city in CITIES:
    BY_COUNTRY[city['code']].append(city)


def normalized(value):
    return ''.join(char for char in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(char))


SEARCH = {city['id']: normalized(' '.join((
    city['name'], city['ru'], city['country'], city['code'],
    COUNTRY_MAP[city['code']].get('ru', ''), city['aliases']))) for city in CITIES}
NAMES = {city['id']: (normalized(city['name']), normalized(city['ru'])) for city in CITIES}
FEATURED = [('Paris', 'FR'), ('Rome', 'IT'), ('London', 'GB'), ('Tokyo', 'JP'),
            ('Bangkok', 'TH'), ('Seoul', 'KR'), ('Singapore', 'SG'), ('Madrid', 'ES'),
            ('Lisbon', 'PT'), ('Amsterdam', 'NL'), ('Prague', 'CZ'), ('Vienna', 'AT'),
            ('Cairo', 'EG'), ('Mexico City', 'MX'), ('Beijing', 'CN'), ('Bishkek', 'KG'),
            ('Tashkent', 'UZ'), ('Astana', 'KZ'), ('Tbilisi', 'GE'), ('Yerevan', 'AM'),
            ('Ottawa', 'CA'), ('Canberra', 'AU'), ('Wellington', 'NZ')]
FEATURED_RANK = {pair: rank for rank, pair in enumerate(FEATURED)}


def daily_budget(code):
    """Editable planning scenarios in USD, never live destination prices."""
    if code in {'KG', 'UZ', 'KZ', 'GE', 'AM', 'IN', 'NP', 'VN', 'TH', 'ID', 'LK', 'LA', 'KH', 'MA', 'EG', 'AL'}:
        return 50
    if code in {'CH', 'NO', 'IS', 'DK', 'US', 'AU', 'NZ', 'SG'}:
        return 180
    if code in {'TR', 'MX', 'PE', 'CO', 'BO', 'RS', 'BG', 'RO', 'PL', 'HU', 'MY', 'PH'}:
        return 75
    return 100


def destination(city):
    country = COUNTRY_MAP[city['code']]
    daily = daily_budget(city['code'])
    result = dict(id=city['id'], name=city['name'], ru=city['ru'],
                  country=city['country'], country_ru=country.get('ru', city['country']),
                  code=city['code'], continent=city['continent'], lat=city['lat'], lon=city['lon'],
                  currency=country.get('currency', ''), population=city['population'],
                  capital=city['capital'], category='culture', days=5, cost=daily * 5,
                  daily=daily, budgetIsEstimate=True, image='',
                  tag='Make this city your next chapter', tag_ru='Новая глава вашего путешествия')
    selected_photo = PHOTOS.get(city['id'], {})
    if selected_photo.get('photo'):
        result.update(selected_photo)
        result.update(photoScope='city', photoLabel=city['name'], photoLabelRu=city['ru'])
    else:
        country_photo = COUNTRY_PHOTOS.get(city['code'], {})
        if country_photo.get('photo'):
            # A country photograph must never acquire a city-specific caption or guide.
            result.update({key: country_photo[key] for key in
                           ('photo', 'photoSource', 'author', 'license') if key in country_photo})
            result.update(photoScope='country', photoLabel=country['name'],
                          photoLabelRu=country.get('ru', country['name']))
    return result


def search(query):
    args = parse_qs(query[:4096])
    query_text = normalized(args.get('q', [''])[0][:100].strip())
    terms = query_text.split()
    code = args.get('country', [''])[0].strip().upper()
    continent = args.get('continent', [''])[0].strip().upper()
    try:
        requested_page = max(1, int(args.get('page', ['1'])[0]))
    except ValueError:
        requested_page = 1
    source = BY_COUNTRY.get(code, ()) if code else CITIES
    rows = [city for city in source
            if (not continent or city['continent'] == continent)
            and all(term in SEARCH[city['id']] for term in terms)]
    order = args.get('sort', ['featured'])[0]
    if order == 'name':
        name_index = 1 if args.get('lang', ['en'])[0] == 'ru' else 0
        rows.sort(key=lambda city: (NAMES[city['id']][name_index], city['id']))
    elif order == 'budget':
        rows.sort(key=lambda city: (daily_budget(city['code']), -city['population'], city['id']))
    elif order == 'population':
        rows.sort(key=lambda city: (-city['population'], city['id']))
    else:
        rows.sort(key=lambda city: (
            bool(query_text) and query_text not in NAMES[city['id']],
            FEATURED_RANK.get((city['name'], city['code']), 999),
            city['id'] not in PHOTOS, not city['capital'], -city['population'], city['id']))
    total = len(rows)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(requested_page, pages)
    start = (page - 1) * PAGE_SIZE
    return {'items': [destination(city) for city in rows[start:start + PAGE_SIZE]],
            'total': total, 'page': page, 'pages': pages, 'pageSize': PAGE_SIZE,
            'cityCount': len(CITIES), 'countryCount': len(COUNTRIES),
            'countriesWithCities': len(COUNTRY_CODES)}

