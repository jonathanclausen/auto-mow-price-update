from woocommerce import API

def get_woo_connection(url, public, secret):
    api = API(
    url=url,
    consumer_key=public,
    consumer_secret=secret,
    version="wc/v3",
    query_string_auth=True
    )

    return api

def round_to_nearest_half(number):
    return round(number * 2) / 2