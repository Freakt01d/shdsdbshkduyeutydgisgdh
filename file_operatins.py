import pandas as pd

# Sample DataFrames
data_csv = pd.DataFrame({
    'common_key_column': [1, 2, 1, 2],
    'instrument_type': ['Bond', 'Stock', 'Bond', 'Stock'],
    'customer_type': ['customer', 'non_customer', 'customer', 'non_customer'],
    'trade_id': [101, 102, 103, 104],
    'amount': [1000, 2000, 1500, 2500]
})

data_xlsx = pd.DataFrame({
    'common_key_column': [1, 2],
    'other_info': [200, 400]
})

# Merge DataFrames
merged_data = pd.merge(data_csv, data_xlsx, on='common_key_column', how='inner')

# Create Pivot Table
pivot_table = pd.pivot_table(merged_data,
                             values=['trade_id', 'amount'],
                             index='instrument_type',
                             columns='customer_type',
                             aggfunc={'trade_id': pd.Series.nunique, 'amount': 'sum'},
                             fill_value=0)

# Adding new total columns for each instrument_type
pivot_table['Total_trades'] = pivot_table[('trade_id', 'customer')] + pivot_table[('trade_id', 'non_customer')]
pivot_table['Total_amount'] = pivot_table[('amount', 'customer')] + pivot_table[('amount', 'non_customer')]

# Add grand total row at the bottom
pivot_table.loc['Grand Total'] = pivot_table.sum()

# Save the pivot table to an Excel file with formatting
with pd.ExcelWriter('output_pivot_table_with_totals.xlsx', engine='xlsxwriter') as writer:
    pivot_table.to_excel(writer, sheet_name='Pivot Table with Totals')

    # Get the xlsxwriter workbook and worksheet objects
    workbook  = writer.book
    worksheet = writer.sheets['Pivot Table with Totals']

    # Define a format for the column headers
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',  # Light green background
        'border': 1
    })

    # Define a number format for the data cells
    number_format = workbook.add_format({'num_format': '#,##0'})

    # Define a format for the 'Grand Total' row
    total_format = workbook.add_format({
        'bold': True,
        'bg_color': '#FFA07A',  # Light salmon background
        'border': 1,
        'num_format': '#,##0'
    })

    # Set the column widths and format for each column
    for col_num, value in enumerate(pivot_table.columns.values):
        worksheet.write(0, col_num + 1, value, header_format)
        worksheet.set_column(col_num + 1, col_num + 1, 18, number_format)

    # Format the 'Grand Total' row
    worksheet.write('A' + str(len(pivot_table)), 'Grand Total', total_format)
    for col_num in range(len(pivot_table.columns)):
        worksheet.write(len(pivot_table) - 1, col_num + 1, pivot_table.iloc[-1, col_num], total_format)
        