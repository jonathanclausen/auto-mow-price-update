import pandas as pd
import os

# Cols must include Product Code
def read_price_csv(path, use_cols):
    df = pd.read_csv(path, 
                    delimiter=";", 
                    usecols=use_cols,
                    dtype={'Product Code': str} )
    df.rename(columns={'Product Code': 'SKU'}, inplace=True)
    # Drop rows where both 'SKU' and 'EUR Distributor price' are NaN
    df_cleaned = df.dropna(how='all')

    # Filter rows where either 'SKU' or 'EUR Distributor price' is missing (NaN)
    missing_values = df_cleaned[df_cleaned.isna().any(axis=1)]

    # Select rows without any missing values
    non_missing_values = df_cleaned[~df_cleaned.isna().any(axis=1)]
    print("Following rows are missing values:")
    print(missing_values.to_string())

    return non_missing_values