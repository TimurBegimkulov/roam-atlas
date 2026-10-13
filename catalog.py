"""Offline GeoNames city index. No external API is needed for search."""
import gzip
import json
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs
ROOT=Path(__file__).parent
with gzip.open(ROOT/'cities.json.gz','rt',encoding='utf-8') as stream: CITIES=json.load(stream)
COUNTRIES=json.loads((ROOT/'countries.json').read_text(encoding='utf-8'))
PHOTOS=json.loads((ROOT/'photos.json').read_text(encoding='utf-8'))
COUNTRY_CODES={city['code'] for city in CITIES}
COUNTRIES=[c for c in COUNTRIES if c['code'] in COUNTRY_CODES]
COUNTRY_MAP={c['code']:c for c in COUNTRIES}
BY_ID={c['id']:c for c in CITIES}
def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))
SEARCH={c['id']:normalized(c['name']+' '+c['ru']+' '+c['country']+' '+COUNTRY_MAP[c['code']].get('ru','')+' '+c['aliases']) for c in CITIES}
def destination(c):
    daily=100
    if c['code'] in 'KG UZ KZ GE AM IN NP VN TH ID LK LA KH MA EG AL'.split(): daily=50
    elif c['code'] in 'CH NO IS DK US AU NZ SG'.split(): daily=180
    elif c['code'] in 'TR MX PE CO BO RS BG RO PL HU MY PH'.split(): daily=75
    return dict(id=c['id'],name=c['name'],ru=c['ru'],country=c['country'],country_ru=COUNTRY_MAP[c['code']].get('ru',c['country']),code=c['code'],continent=c['continent'],lat=c['lat'],lon=c['lon'],category='culture',days=5,cost=daily*5,daily=daily,image='',tag='Make this city your next chapter',tag_ru='Новая глава вашего путешествия',**PHOTOS.get(c['id'],{}))
def search(query):
    args=parse_qs(query)
    q=normalized(args.get('q',[''])[0][:100]);code=args.get('country',[''])[0][:2]
    try:page=max(1,min(2000,int(args.get('page',['1'])[0])))
    except ValueError:page=1
    rows=[c for c in CITIES if (not code or c['code']==code) and all(term in SEARCH[c['id']] for term in q.split())]
    order=args.get('sort',['featured'])[0]
    if order=='name':rows.sort(key=lambda c:c['name'])
    elif order=='budget':rows.sort(key=lambda c:destination(c)['cost'])
    elif order=='population':rows.sort(key=lambda c:-c['population'])
    else:
        featured=['Paris','Rome','London','Tokyo','Bangkok','Seoul','Singapore','Madrid','Lisbon','Amsterdam','Prague','Vienna','Cairo','Mexico City','Beijing','Bishkek','Tashkent','Astana','Tbilisi','Yerevan','Ottawa','Canberra','Wellington']
        codes='FR IT GB JP TH KR SG ES PT NL CZ AT EG MX CN KG UZ KZ GE AM CA AU NZ'.split()
        rank={(name,code):i for i,(name,code) in enumerate(zip(featured,codes))}
        rows.sort(key=lambda c:(bool(q) and normalized(c['name'])!=q and normalized(c['ru'])!=q,rank.get((c['name'],c['code']),999),c['id'] not in PHOTOS,not c['capital'],-c['population']))
    total=len(rows);start=(page-1)*24
    return {'items':[destination(c) for c in rows[start:start+24]],'total':total,'page':page,'pages':max(1,(total+23)//24),'cityCount':len(CITIES),'countryCount':len({c['code'] for c in CITIES})}
