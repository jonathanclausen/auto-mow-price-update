import sys
import os
import json
import update_dealer_prices
import update_dynamic_prices
import shared

UPDATE_DISTRIBUTOR_COMMAND = "--update-distributor"
UPDATE_DEALER_COMMAND = "--update-dealer"

def main(csv_filepath, update_dealer, update_distributor, config):
    wc_api = shared.get_woo_connection(config['url'], config['api-public'], config['api-secret'])

    if (update_dealer):
        dealer_updater = update_dealer_prices.DealerPriceUpdate(csv_filepath, wc_api, config)
        dealer_updater.update_dealer_prices()
    if (update_distributor):
        distributor_updater = update_dynamic_prices.DistributorPriceUpdate(csv_filepath, wc_api, config)
        distributor_updater.update_distributor_prices()

if __name__ == "__main__":
    
    update_distributor = False
    update_dealer = False
    
    if not len(sys.argv) > 1:
        print("No file given")
        exit()
    if not len(sys.argv) > 2:
        print("No operation given. Use either or both of '--update-distributor', '--update-dealer'")
        exit()

    csv_filepath = sys.argv[1]
    if not os.path.isfile(csv_filepath):
        print("Path is not a file. First argument must be the csv file path")
        exit()

    if UPDATE_DISTRIBUTOR_COMMAND in sys.argv:
        update_distributor = True
    if UPDATE_DEALER_COMMAND in sys.argv:
        update_dealer = True

    with open('config.json', 'r') as file:
        config = json.load(file)

    main(csv_filepath, update_dealer, update_distributor, config)