import pandas as pd
import os


def read_price_csv(path):
    df = pd.read_csv(path, 
                    delimiter=";", 
                    usecols=['Product Code','EUR Distributor price', 'DKK Distributor price', 'USD Distributor price2', 'GBP Distributor Price'],
                    dtype={'Product Code': str} )
    df.rename(columns={'Product Code': 'SKU'}, inplace=True)


    # Drop rows where both 'SKU' and 'EUR Distributor price' are NaN
    df_cleaned = df.dropna(subset=['SKU', 'EUR Distributor price', 'DKK Distributor price', 'USD Distributor price2', 'GBP Distributor Price'], how='all')

    # Filter rows where either 'SKU' or 'EUR Distributor price' is missing (NaN)
    missing_values = df_cleaned[df_cleaned['SKU'].isna() | 
                                df_cleaned['EUR Distributor price'].isna() | 
                                df_cleaned['DKK Distributor price'].isna() | 
                                df_cleaned['USD Distributor price2'].isna() | 
                                df_cleaned['GBP Distributor Price'].isna()]
    # Print each row with missing values
    for index, row in missing_values.iterrows():
        print(f"Row index {index}:")
        print(row)
        print()  # Print a newline for better readability

    return df