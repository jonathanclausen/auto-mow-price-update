import pandas as pd
import json
import read_price_csv
import shared

class DealerPriceUpdate:
    def __init__(self, csv_filepath, wc_api):

        self.csv_filepath = csv_filepath
        self.wc_api = wc_api

        self.error_outfile = "update_dealer_prices-error.csv"
        self.success_outfile = "update-dealer-prices-success.csv"
        
        self.cols = ["Product Code","DKK Dealer Price","EUR Dealer price","USD Dealer price","GBP Dealer Price"]
        self.price_df = read_price_csv.read_price_csv(csv_filepath, self.cols)

        self.errorList = []
        self.successList = []
        self.error_count = 0
        self.success_count = 0

    def getProductFromSKU(self, sku):
        r = self.wc_api.get("products", params={"sku": sku})
        
        if (int(r.status_code) != 200):
            print("Could not find a product with SKU " + str(sku))
            print("Status code: "+ str(r.status_code))
            self.errorList.append(f"error in request. status_code: {r.status_code}, SKU: {sku}")

        json = r.json()
        return json, r.status_code

    def update_dealer_prices(self):
        
        products = self.price_df

        for row in products.iterrows():
            data = row[1]

            sku = data["SKU"]
            eur_price = shared.round_to_nearest_half(data["EUR Dealer price"])
            dkk_price = shared.round_to_nearest_half(data["DKK Dealer Price"])
            gbp_price = shared.round_to_nearest_half(data["GBP Dealer Price"])
            usd_price = shared.round_to_nearest_half(data["USD Dealer price"])

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

            json, status_code = self.getProductFromSKU(sku)
            if (status_code != 200):
                print(f"Could not connect to {endpoint}. status_code: {r.status_code}")
                self.errorList.append(f"Could not connect to {endpoint}. status_code: {r.status_code}")
                self.error_count += 1
                continue
                
            if (json == []):
                print("Product with SKU " + str(sku) + " not found")
                self.errorList.append(f"SKU: {sku} not found.")
                self.error_count += 1
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

            r = self.wc_api.get(endpoint)
            json = r.json()
            if (r.status_code != 200):
                print(f"Could not connect to {endpoint}. status_code: {r.status_code}")
                self.errorList.append(f"Could not connect to {endpoint}. status_code: {r.status_code}")
                self.error_count += 1
                continue
                
            if (json == []):
                print("Product with SKU " + str(sku) + " not found")
                self.errorList.append(f"SKU: {sku} not found.")
                self.error_count += 1
                continue

            print("endpoint: " + endpoint)

            r = self.wc_api.put(endpoint, body)
            if (int(r.status_code) != 200):
                msg = "Could not update product with sku " + str(sku) + " and endpoint " + endpoint + " status_code: " + r.status_code
                print(msg)
                self.errorList.append(msg)
                continue
            
            msg = f"Updated {str(sku)}: EUR: {eur_price}, DKK: {dkk_price}, GBP: {gbp_price}, USD: {usd_price}"
            print(msg)
            # print("Updated " + str(sku) + " with new price " + str(eur_price))
            self.success_count += 1
            self.successList.append(msg)
            
        # Saving result to file
        error_df = pd.DataFrame(self.errorList)
        success_df = pd.DataFrame(self.successList)
        print("Saving errors to " + self.error_outfile)
        print("Saving updates to " + self.success_outfile)
        print(f"success: {self.success_count}, errors: {self.error_count}, total: {len(products.index)}")
        error_df.to_csv(self.error_outfile, index=False, header=['SKU'])
        success_df.to_csv(self.success_outfile, index=False, header=['SKU'])