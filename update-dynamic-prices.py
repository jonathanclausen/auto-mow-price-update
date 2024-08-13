from woocommerce import API
import json
import read_price_csv
import pandas as pd

with open('config.json', 'r') as file:
    config = json.load(file)


wcapi = API(
    url="https://auto-mow.com",
    consumer_key=config['api-public'],
    consumer_secret=config['api-secret'],
    version="wc/v3"
)

currencies = {
    "eu": {
        "metadata_name": "pricing_rules",
        "csv_name": "EUR Distributor price"
    },
    "uk": {
        "metadata_name": "_uk_pricing_rules",
        "csv_name": "GBP Distributor Price"
    },
    "us": {
        "metadata_name": "_us_pricing_rules",
        "csv_name": "USD Distributor price2"
    },
    "dk":{
        "metadata_name": "_danmark_pricing_rules",
        "csv_name": "DKK Distributor price"
    }

}

update_stats = {}

price_df = read_price_csv.read_price_csv("Ark1.csv")

def update_stat(sku, currency, old_price, new_price):
    if not sku in update_stats:
        update_stats[sku] = [
            {
                currency: {
                    "old_price": old_price,
                    "new_price": new_price,
                }
            }
        ]
        
    else:
        update_stats[sku].append(
            {
                currency: {
                    "old_price": old_price,
                    "new_price": new_price,
                }
            }
        )

def get_sku_of_variation(variation_id):
    p = wcapi.get(f"products/{variation_id}").json()
    return p['sku']

def get_distributor_price_for_sku(sku, currency_csv_name):
    # Filter the DataFrame to find the row with the matching SKU
    row = price_df[price_df['SKU'] == sku]
    
    if not row.empty:
        # Retrieve the price from the filtered row
        return row[currency_csv_name].values[0]
    else:
        return None  # SKU not found

def sku_with_price_exists(sku, currency_csv_name):
    # Filter the DataFrame to find the row with the matching SKU
    row = price_df[price_df['SKU'] == sku]
    
    if not row.empty:
        # Check if the price is not NaN
        if pd.notna(row[currency_csv_name].values[0]):
            return True
    return False

#currency is a constant used to index correct metadata. Set is the meta data set to edit.
def update_currencies(set, sku, metadata):
    for currency, info in currencies.items():
        currency_metadata = next((x for x in metadata if x["key"] == info['metadata_name']), None)
        if not currency_metadata: continue

        price = get_distributor_price_for_sku(sku, info['csv_name'])

        first_price_rule = currency_metadata.get('value').get(set).get("rules").get("1")

        update_stat(sku, currency, first_price_rule['amount'], price)

        first_price_rule['price_method'] = "manual"
        first_price_rule['amount'] = str(price)
        


def update_product_distributor_price(product_id):
    p = wcapi.get(f"products/{product_id}").json()
    has_variations = len(p['variations']) > 0
    has_changed = False

    meta_data = p['meta_data']

    pricing_rules = next((x for x in meta_data if x["key"] == '_pricing_rules'), None)

    # Check if the product should have distributor price setup even though it has not.
    if not pricing_rules:
        skus_to_check = []
        if has_variations:
            
            for v_id in p['variations']:
                skus_to_check.append(get_sku_of_variation(v_id))
        else:
            skus_to_check.append(p['sku'])

        for sku in skus_to_check:
            if sku_with_price_exists(sku, currencies["eu"]["csv_name"]):
                print(f"SKU {sku} has distributor price but no distributor setup")
        return

    values_dict = pricing_rules.get("value")

    skus_changed = []
    for set_key, set in values_dict.items():
        distributor = False
        conditions_dict = set.get("conditions")
        for cond_key, condition in conditions_dict.items():
            roles_list = condition.get("args").get('roles')
            if roles_list and 'distributor' in roles_list:
                distributor = True
                break

        if not distributor:
            continue

        sku = ""
        if (has_variations):
            variations_list = set.get('variation_rules').get('args').get('variations')
            if not variations_list:
                continue
            if len(variations_list) != 1:
                print(f"Set {set_key} in product {product_id} has more than variation for distributor price. Not allowed")
                continue
            sku = get_sku_of_variation(variations_list[0])
        else:
            sku = p['sku']

        if not sku:
            print(f"No SKU found for products in set {set_key} for product {product_id}")

        rules = set.get('rules')
        
        if not rules:
            continue
        if len(rules) != 1:
            print(f"Set {set_key} in product {product_id} has more than one price rule. Cannot decide which to change")
            continue

        for rule_key, rule in rules.items():
            if rule.get('type') == 'fixed_price':
                new_price = get_distributor_price_for_sku(sku, currencies["eu"]['csv_name'])
                if (new_price):
                    update_stat(sku, "eu", rule['amount'], new_price)
                    print(f"Changing price of {sku} from {rule['amount']} to {str(new_price)}")
                    rule['amount'] = str(new_price)
                    update_currencies(set_key, sku, meta_data)
                    has_changed = True
                else:
                    print(f"No distributor price found for product with sku {sku}")

    if (has_changed):
        
        uk_pricing_rules = next((x for x in meta_data if x["key"] == currencies["uk"]['metadata_name']), None)
        us_pricing_rules = next((x for x in meta_data if x["key"] == currencies["us"]['metadata_name']), None)
        dk_pricing_rules = next((x for x in meta_data if x["key"] == currencies["dk"]['metadata_name']), None)
        
        body = {
            "meta_data": [
                pricing_rules,
                uk_pricing_rules,
                us_pricing_rules,
                dk_pricing_rules
            ]
        }
        wcapi.put(f"products/{product_id}", body)


def get_all_product_ids():
    product_ids = []
    page = 1
    per_page = 50  # Number of products per page (max 100)
    
    while True:
        # Fetch products from WooCommerce API
        response = wcapi.get("products", params={"per_page": per_page, "page": page, "status": "publish"})
        products = response.json()
        
        # If no products are returned, exit the loop
        if not products:
            break
        
        # Extract product IDs
        for product in products:
            product_ids.append(product['id'])
        
        # Increment page number to get the next page of products
        page += 1

    return product_ids

# Fetch and print all product IDs
all_product_ids = get_all_product_ids()

#all_product_ids = [13321] #13075 #15473

count = 1
for id in all_product_ids:
    print(f"{count} of {len(all_product_ids)}. id: {id}")
    update_product_distributor_price(id)
    count += 1

with open("update-statistics", "w") as fp:
    json.dump(update_stats, fp) 