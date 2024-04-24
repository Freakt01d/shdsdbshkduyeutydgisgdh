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

# Export the pivot table to Excel
output_file = 'detailed_pivot_table.xlsx'
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    pivot_table.to_excel(writer, sheet_name='Detailed View', index=False)

    # Access the workbook and the worksheet
    workbook = writer.book
    worksheet = writer.sheets['Detailed View']

    # Apply a format for clear visibility
    header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D7E4BC'})
    for col_num, value in enumerate(pivot_table.columns.values):
        worksheet.write(0, col_num, value, header_format)

    # Set the column width
    worksheet.set_column('A:B', 20)
    worksheet.set_column('C:D', 18)

# Users will need to manually set up grouping in Excel to create a collapsible structure.
