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

# Filtering data as needed
filtered_data = data[(data['CUSTOMERTYPE'] == 'noncustomer') & (~data['INSTRUMENT_TYPE'].isin(['Cash_Securities']))]

# Create a pivot table
pivot_table = pd.pivot_table(
    filtered_data,
    index=['INSTRUMENT_TYPE', 'PRODUCT_STRUCTURE_TYPE'],
    values=['ABS_EXCHANGEDAMOUNT_USD', 'COUNTERP_TRADEPARTYID'],
    aggfunc={'ABS_EXCHANGEDAMOUNT_USD': np.sum, 'COUNTERP_TRADEPARTYID': 'count'},
    fill_value=0,
    margins=True,
    margins_name='Grand Total'
)

# Flatten the MultiIndex to make it suitable for Excel grouping
pivot_table.reset_index(inplace=True)
pivot_table.sort_values(by=['INSTRUMENT_TYPE', 'PRODUCT_STRUCTURE_TYPE'], inplace=True)

# Create a new DataFrame with instrument types and sub-products listed in a single column
dropdown_list = []
for instrument_type, group in pivot_table.groupby('INSTRUMENT_TYPE'):
    dropdown_list.append(instrument_type)
    dropdown_list.extend(['  ' + sub_product for sub_product in group['PRODUCT_STRUCTURE_TYPE']])

# Export the pivot table to Excel with the dropdown list
output_file = 'pivot_table_with_dropdown.xlsx'
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    # Create a DataFrame with dropdown list
    dropdown_df = pd.DataFrame({'Dropdown': dropdown_list})
    dropdown_df.to_excel(writer, sheet_name='Dropdown List', index=False)

    # Write the pivot table to a separate sheet
    pivot_table.to_excel(writer, sheet_name='Pivot Table', index=False)

# Users can manually reference the dropdown list and select the instrument type or sub-product.