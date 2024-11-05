import pandas as pd
import json
from woocommerce import API
import read_price_csv


# Functions

def getProductFromSKU(sku):
    r = wcapi.get("products", params={"sku": sku})
    
    if (int(r.status_code) != 200):
        print("Could not find a product with SKU " + str(sku))
        print("Status code: "+ str(r.status_code))
        errorList.append(f"error in request. status_code: {r.status_code}, SKU: {sku}")

    json = r.json()
    return json, r.status_code

# Set environment
is_staging = False

wcapi = API.connect_to_api(is_staging)

error_outfile = "results/ErrorUpdateMultipeCurrencyProductPricesResult.csv"
success_outfile = "results/SuccessUpdateMultipeCurrencyProductPricesResult.csv"

# Get data - a csv with columns (sku, price)
colsToUse = ["Product Code","DKK Dealer Price","EUR Dealer price","USD Dealer price","GBP Dealer Price"]
products = read_price_csv.getProductPricesFromCsv("/Users/jonathan/concensurTools/Auto-Mow/WoocommerceAPI/Data/prices-04-11-2024.csv", colsToUse)

errorList = []
successList = []
error_count = 0
success_count = 0

for row in products.iterrows():
    data = row[1]

    sku = data["SKU"]
    eur_price = round(data["EUR Dealer price"])
    dkk_price = round(data["DKK Dealer Price"])
    gbp_price = round(data["GBP Dealer Price"])
    usd_price = round(data["USD Dealer price"])

    # TODO: Change body here:
    body = {
        "regular_price": str(eur_price),
        "meta_data": 
        [
            {
                "key": "_uk_price_method",
                "value": "manual"
            },
            {
                "key": "_uk_regular_price",
                "value": gbp_price
            },
            {
                "key": "_uk_price",
                "value": gbp_price
            },
            {
                "key": "_danmark_price_method",
                "value": "manual"
            },
            {
                "key": "_danmark_regular_price",
                "value": dkk_price
            },
            {
                "key": "_danmark_price",
                "value": dkk_price
            },
            {
                "key": "_us_price_method",
                "value": "manual"
            },
            {
                "key": "_us_regular_price",
                "value": usd_price
            },
            {
                "key": "_us_price",
                "value": usd_price
            }
        ]
    }

    json, status_code = getProductFromSKU(sku)
    if (status_code != 200):
        print(f"Could not connect to {endpoint}. status_code: {r.status_code}")
        errorList.append(f"Could not connect to {endpoint}. status_code: {r.status_code}")
        error_count += 1
        continue
        
    if (json == []):
        print("Product with SKU " + str(sku) + " not found")
        errorList.append(f"SKU: {sku} not found.")
        error_count += 1
        continue

    parent_id = int(json[0]['parent_id'])
    product_id = int(json[0]['id'])

    endpoint = ""
    variable_product = False
    # variable product
    if (parent_id != 0 ):
        endpoint = "products/" + str(parent_id) + "/variations/" + str(product_id)
        variable_product = True
    # simple product
    else:
        endpoint = "products/" + str(product_id)
    #second request

    r = wcapi.get(endpoint)
    json = r.json()
    if (r.status_code != 200):
        print(f"Could not connect to {endpoint}. status_code: {r.status_code}")
        errorList.append(f"Could not connect to {endpoint}. status_code: {r.status_code}")
        error_count += 1
        continue
        
    if (json == []):
        print("Product with SKU " + str(sku) + " not found")
        errorList.append(f"SKU: {sku} not found.")
        error_count += 1
        continue

    # pricing_rule = CheckPriceRuleExists(json['meta_data'], product_id)
    # if pricing_rule:
    #     update_pricing_rule = UpdatePriceRule(json['meta_data'], product_id, pricing_rule, eur_price, dkk_price, gbp_price, usd_price)

    print("endpoint: " + endpoint)

    r = wcapi.put(endpoint, body)
    if (int(r.status_code) != 200):
        msg = "Could not update product with sku " + str(sku) + " and endpoint " + endpoint + " status_code: " + r.status_code
        print(msg)
        errorList.append(msg)
        continue
    
    msg = f"Updated {str(sku)}: EUR: {eur_price}, DKK: {dkk_price}, GBP: {gbp_price}, USD: {usd_price}"
    print(msg)
    # print("Updated " + str(sku) + " with new price " + str(eur_price))
    success_count += 1
    successList.append(msg)
    
# Saving result to file
error_df = pd.DataFrame(errorList)
success_df = pd.DataFrame(successList)
print("Saving errors to " + error_outfile)
print("Saving updates to " + success_outfile)
print(f"success: {success_count}, errors: {error_count}, total: {len(products.index)}")
error_df.to_csv(error_outfile, index=False, header=['SKU'])
success_df.to_csv(success_outfile, index=False, header=['SKU'])


