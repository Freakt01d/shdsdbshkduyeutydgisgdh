import pandas as pd
import numpy as np

# Sample data - replace this with your actual DataFrame
data = pd.DataFrame({
    'INSTRUMENT_TYPE': ['Bond', 'Bond', 'Stock', 'Stock', 'Bond', 'Stock'],
    'PRODUCT_STRUCTURE_TYPE': ['SubType1', 'SubType2', 'SubType1', 'SubType2', 'SubType3', 'SubType3'],
    'CUSTOMERTYPE': ['customer', 'noncustomer', 'customer', 'noncustomer', 'customer', 'noncustomer'],
    'ABS_EXCHANGEDAMOUNT_USD': [100, 200, 300, 400, 150, 250],
    'COUNTERP_TRADEPARTYID': [1, 2, 1, 2, 1, 2]
})

# Filter data by instrument type
instrument_types = data['INSTRUMENT_TYPE'].unique()
dropdown_list = []

for instrument_type in instrument_types:
    # Filter data by instrument type
    filtered_data = data[data['INSTRUMENT_TYPE'] == instrument_type]
    
    # Retrieve sub-products for the current instrument type
    sub_products = filtered_data['PRODUCT_STRUCTURE_TYPE'].astype(str).unique()  # Convert to string
    
    # Add instrument type and sub-products to dropdown list
    dropdown_list.append(instrument_type)
    dropdown_list.extend(['  ' + sub_product for sub_product in sub_products])

# Export the dropdown list to Excel
dropdown_df = pd.DataFrame({'Dropdown': dropdown_list})
dropdown_df.to_excel('dropdown_list.xlsx', index=False)
