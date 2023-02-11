import json
import requests
import time

from datetime import datetime
from pymongo import MongoClient
from pyquery import PyQuery

def get_properties(number = 0):
    # https://hoppscotch.io/
    url = "https://www.centris.ca/Property/GetInscriptions"

    payload = {"startPosition": 0}
    headers = {
        "content-type": "application/json",
        "Cache-Control": "no-cache",
        "Content-Length": "20",
        "Host": "www.centris.ca",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.centris.ca/fr/propriete~a-vendre?view=Thumbnail"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    responseJson = json.loads(response.text)
    totalNumberOfProperties = number if number != 0 else responseJson['d']['Result']['count']
    propertiesPerPage = responseJson['d']['Result']['inscNumberPerPage']
    startPosition = 0

    properties = []
    while startPosition < totalNumberOfProperties:
        payload['startPosition'] = startPosition
        time.sleep(1)
        response = requests.request("POST", url, json=payload, headers=headers)
        responseJson = json.loads(response.text)
        html = responseJson['d']['Result']['html']
        pq = PyQuery(html)

        for propertyItem in pq('.shell').items():
            if ('/pied carré' in propertyItem('.price span').text() or 
                '/mètre carré' in propertyItem('.price span').text() or 
                '/acre' in propertyItem('.price span').text()):
                continue
            property = {
                "_id": propertyItem('.a-more-detail').attr('data-mlsnumber'),
                "thumbnail_url": propertyItem('.property-thumbnail-summary-link img').attr('src'),
                "property_url": propertyItem('.property-thumbnail-summary-link').attr('href'),
                "asking_prices": 
                [
                    {
                        "as_of_date": datetime.today().strftime('%Y-%m-%d'), 
                        "price": int(propertyItem('.price span').text().replace('$', '').replace('+TPS/TVQ', '').replace('\xa0', '').strip())
                    }
                ],
                "is_taxable": '+TPS/TVQ' in propertyItem('.price span.desc').text(),
                "category": propertyItem('span.category div').text(),
                "street": propertyItem('span.address div').eq(0).text(),
                "city": propertyItem('span.address div').eq(1).text(),
                "lat": propertyItem('.ll-match-score').attr('data-lat'),
                "lng": propertyItem('.ll-match-score').attr('data-lng'),
                "land_area_sqft": propertyItem('.land-area span').text().replace('pc', '').replace(' ', '').strip(),
                "bedroom": propertyItem('.cac').text(),
                "bathroom": propertyItem('.sdb').text(),
                "is_active": True,
                "created_date": datetime.now(),
                "last_modified_date": datetime.now() 
            }
            properties.append(property)

        startPosition += propertiesPerPage

    return properties

def upsert_properties(properties):
    client = MongoClient('mongodb+srv://gpare-dev:SECRET@gpare-dev-cluster.by9wxbq.mongodb.net/?retryWrites=true&w=majority')
    db = client.test
    collection = db.Properties

    for property in properties:
        dbProperty = collection.find_one({'_id': property['_id']})
        if (dbProperty is None):
            collection.insert_one(property)
        else:
            if not any(asking_price['price'] == property['asking_prices'][0]['price'] for asking_price in dbProperty['asking_prices']):
                collection.update_one(
                    {'_id': property['_id']}, 
                    {"$set": {"last_modified_date": datetime.now()}}
                )
                collection.update_one(
                    {'_id': property['_id']}, 
                    {"$addToSet": {"asking_prices": property['asking_prices'][0]}}
                )
    
    dbProperties = collection.find()
    for dbProperty in dbProperties:
        if next((item for item in properties if item["_id"] == dbProperty['_id']), None) is None:
            collection.update_one(
                {'_id': dbProperty['_id']}, 
                {"$set": {"is_active": False, "last_modified_date": datetime.now()}}
            )

upsert_properties(get_properties())