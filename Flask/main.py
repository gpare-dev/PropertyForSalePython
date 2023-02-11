from flask import Flask
from flask import render_template
from pymongo import MongoClient

app = Flask(__name__)

@app.route("/")
def index():
    client = MongoClient('mongodb+srv://gpare-dev:SECRET@gpare-dev-cluster.by9wxbq.mongodb.net/?retryWrites=true&w=majority')
    db = client.test
    collection = db.Properties

    def sort_by_date(asking_price):
        return asking_price['as_of_date']

    def sort_by_sale_desc(property):
        return property['sale']

    propertiesOnSale = []
    dbProperties = collection.find({"category": {'$nin' : ["Terre à vendre", "Terrain à vendre"]}})
    for dbProperty in dbProperties:
        if (len(dbProperty['asking_prices']) > 1):
            prices = dbProperty['asking_prices'].copy()
            prices.sort(key=sort_by_date)
            originalPrice = prices[0]['price']
            currentPrice = prices[len(prices)-1]['price']
            propertyOnSale = {
                "sale": round((1-(currentPrice / originalPrice)) * 100)*-1,
                "original_price": f"{originalPrice:,}",
                "current_price": f"{currentPrice:,}",
                "url" : "https://www.centris.ca" + dbProperty['property_url'],
                "thumbnail_url": dbProperty['thumbnail_url'],
                "taxable_text": "+TPS/TVQ" if dbProperty['is_taxable'] else ""
            }
            propertiesOnSale.append(propertyOnSale)
    propertiesOnSale.sort(key=sort_by_sale_desc)
    return render_template('index.html', properties=propertiesOnSale)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
