from woocommerce import API
import json
import read_price_csv
import pandas as pd
import time
import random

CURRENCIES = {
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

class DistributorPriceUpdate:
    def __init__(self, csv_filepath, wc_api):

        self.csv_filepath = csv_filepath
        self.wc_api = wc_api
        self.products = self.get_all_products()
        self.cols = ['Product Code','EUR Distributor price', 'DKK Distributor price', 'USD Distributor price2', 'GBP Distributor Price']
        self.price_df = read_price_csv.read_price_csv(csv_filepath, self.cols)
        self.log_list = []
    
    def get_all_products(self):
        params = {}
        params["per_page"] = 20
        page = 1
        all_results = []

        while True:
            params["page"] = page
            response = self.wc_api.get("products", params=params)

            if not response.ok:
                raise Exception(f"Request failed: {response.status_code} - {response.text}")
            
            batch = response.json()
            if not batch:
                break

            all_results.extend(batch)
            page += 1

        return all_results

    def get_variations(self, product_id):
        product_variations = self.wc_api.get(f"products/{product_id}/variations").json()
        return product_variations
        

    def get_distributor_price_for_sku(self, sku, currency_csv_name):
        # Filter the DataFrame to find the row with the matching SKU
        row = self.price_df[self.price_df['SKU'] == sku]
        
        if not row.empty:
            # Retrieve the price from the filtered row
            return row[currency_csv_name].values[0]
        else:
            return None  # SKU not found

    #currency is a constant used to index correct metadata. Set is the meta data set to edit.
    def update_currencies(self, set, sku, metadata):
        for currency, info in CURRENCIES.items():
            currency_metadata = next((x for x in metadata if x["key"] == info['metadata_name']), None)
            if not currency_metadata: continue

            price = self.get_distributor_price_for_sku(sku, info['csv_name'])

            first_price_rule = currency_metadata.get('value').get(set).get("rules").get("1")

            self.update_stat(sku, currency, first_price_rule['amount'], price)

            first_price_rule['price_method'] = "manual"
            first_price_rule['amount'] = str(price)
            
    def get_wc_product_by_id(self, id):
        return next((item for item in self.products if item.get("id") == id), None)

    def get_wc_product_by_sku(self, sku):
            return next((item for item in self.products if item.get("sku") == sku), None)
    
    def update_product_distributor_price(self, product):
        p = product

        has_variations = len(p['variations']) > 0

        eu_pricing_rules = {}
        uk_pricing_rules = {}
        us_pricing_rules = {}
        dk_pricing_rules = {}
        
        if has_variations:
            product_variations = self.get_variations(p['id'])

            for v in product_variations:
                v_id = v["id"]
                
                sku = v["sku"]

                if not sku:
                    self.log(f"No sku found for product with id {v_id}")
                    continue

                new_price = self.get_distributor_price_for_sku(sku, CURRENCIES["eu"]['csv_name'])
                
                if not new_price:
                    self.log(f"No price found for product with id {v_id}, sku {sku}")
                    continue

                set_key = self.generate_set_key()
                eu_pricing_rules[set_key] = self.make_eu_rule(new_price, v_id)
                
                uk_price = self.get_distributor_price_for_sku(sku, CURRENCIES["uk"]['csv_name'])
                self.try_set_price(uk_pricing_rules, set_key, uk_price, v_id, sku)

                us_price = self.get_distributor_price_for_sku(sku, CURRENCIES["us"]['csv_name'])
                self.try_set_price(us_pricing_rules, set_key, us_price, v_id, sku)

                dk_price = self.get_distributor_price_for_sku(sku, CURRENCIES["dk"]['csv_name'])
                self.try_set_price(dk_pricing_rules, set_key, dk_price, v_id, sku)

            meta_data_update = self.create_meta(eu_pricing_rules, uk_pricing_rules, us_pricing_rules, dk_pricing_rules)
            if meta_data_update['meta_data']:
                self.wc_api.put(f"products/{product["id"]}", meta_data_update)

        else:
            sku = p["sku"]
            id = p["id"]
            if not sku:
                self.log(f"No sku found for product with id {id}")
                return

            new_price = self.get_distributor_price_for_sku(sku, CURRENCIES["eu"]['csv_name'])
            
            if not new_price:
                self.log(f"No price found for product with id {id}, sku {sku}")
                return

            set_key = self.generate_set_key()
            eu_pricing_rules[set_key] = self.make_eu_rule(new_price, None)
            
            uk_price = self.get_distributor_price_for_sku(sku, CURRENCIES["uk"]['csv_name'])
            self.try_set_price(uk_pricing_rules, set_key, uk_price, id, sku)
            
            us_price = self.get_distributor_price_for_sku(sku, CURRENCIES["us"]['csv_name'])
            self.try_set_price(us_pricing_rules, set_key, us_price, id, sku)

            dk_price = self.get_distributor_price_for_sku(sku, CURRENCIES["dk"]['csv_name'])
            self.try_set_price(dk_pricing_rules, set_key, dk_price, id, sku)

            meta_data_update = self.create_meta(eu_pricing_rules, uk_pricing_rules, us_pricing_rules, dk_pricing_rules)
            if meta_data_update:
                self.wc_api.put(f"products/{product["id"]}", meta_data_update)

    def create_meta(self, eu_pricing_rules, uk_pricing_rules, us_pricing_rules, dk_pricing_rules):
        meta_data = []
        
        if eu_pricing_rules:
            eu_data = {
                "key": "_pricing_rules",
                "value": eu_pricing_rules
            }
            meta_data.append(eu_data)

        if uk_pricing_rules:
            uk_data = {
                "key": "_uk_pricing_rules",
                "value": uk_pricing_rules
            }
            meta_data.append(uk_data)

        if us_pricing_rules:
            us_data = {
                "key": "_us_pricing_rules",
                "value": us_pricing_rules
            }
            meta_data.append(us_data)

        if dk_pricing_rules:
            dk_data = {
                "key": "_danmark_pricing_rules",
                "value": dk_pricing_rules
            }
            meta_data.append(dk_data)
        
        meta_data_update = {
            "meta_data": meta_data
        }
        return meta_data_update

    def try_set_price(self, rules, set_key, price, id, sku):
        if not price:
            self.log(f"No price found for product with id {id}, sku {sku}")
            return
        else:
            rules[set_key] = self.make_country_rule_for_set(price)



    def update_or_add(self, meta_data, key, value):
        found = False
        for meta in meta_data:
            if meta["key"] == key:
                meta["value"] = value
                found = True
                break

        # If not found, append it
        if not found:
            meta_data.append({
                "key": key,
                "value": value
            })


        
    def log(self, msg):
        self.log_list.append(msg)
        print(msg)


    def generate_set_key(self):
        return "set_" + hex(int(time.time() * 1000000) + random.randint(0, 99999))[2:]


    def make_eu_rule_for_single_product(self, amount):
        update_data = {
            "conditions_type": "all",
            "conditions": {
                "1": {
                    "type": "apply_to",
                    "args": {
                        "applies_to": "roles",
                        "roles": ["distributor"]
                    }
                }
            },
            "collector": {"type": "product"},
            "mode": "continuous",
            "date_from": "",
            "date_to": "",
            "rules": {
                "1": {
                    "from": "",
                    "to": "",
                    "type": "fixed_price",
                    "amount": "186.75"
                }
            },
            "blockrules": {
                "1": {
                    "from": "",
                    "adjust": "",
                    "type": "fixed_adjustment",
                    "amount": "",
                    "repeating": "no"
                }
            }
        }

    def make_eu_rule(self, amount, variation_id):
        pricing_rules = {
            "conditions_type": "all",
            "conditions": {
                "1": {
                    "type": "apply_to",
                    "args": {
                        "applies_to": "roles",
                        "roles": ["distributor"]
                    }
                }
            },
            "collector": {
                "type": "product"
            },
            
            "mode": "continuous",
            "date_from": "",
            "date_to": "",
            "rules": {
                "1": {
                    "from": "",
                    "to": "",
                    "type": "fixed_price",
                    "amount": str(amount)
                }
            },
            "blockrules": {
                "1": {
                    "from": "",
                    "adjust": "",
                    "type": "fixed_adjustment",
                    "amount": "",
                    "repeating": "no"
                }
            }
        }

        if variation_id:
            pricing_rules['variation_rules'] = {
                "args": {
                    "type": "variations",
                    "variations": [variation_id]
                }
            }

        return pricing_rules
    
    def make_country_rule_for_set(self, price):
        pricing_dict = {
            "rules": {
                "1": {
                    "price_method": "manual",
                    "amount": str(price)
                }
            },
            "blockrules": {
                "1": {
                    "price_method": "exchange_rate",
                    "amount": ""
                }
            }
        }
        return pricing_dict

    def update_distributor_prices(self):
        count = 1
        for product in self.products:
            print(f"{count} of {len(self.products)}. id: {product["id"]}")
            self.update_product_distributor_price(product)
            count += 1

        return self.log_list