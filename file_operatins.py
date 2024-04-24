vm7_data = pd.DataFrame({
    'count': (pivot_table['trade_id_customer'] / pivot_table['Total_trades']) * 100,
    'amount': (pivot_table['amount_customer'] / pivot_table['Total_amount']) * 100
})

# Optionally, rename the index
vm7_data.index.name = 'instrument_type'

# Save the pivot table to an Excel file with formatting
with pd.ExcelWriter('output_pivot_table_with_totals.xlsx', engine='xlsxwriter') as writer:
    pivot_table.to_excel(writer, sheet_name='Pivot Table with Totals', startrow=0, startcol=0)

    # Start vm7_data right after the last column of pivot_table
    vm7_start_col = len(pivot_table.columns) + 2  # Plus 2 for a little space

    vm7_data.to_excel(writer, sheet_name='Pivot Table with Totals', startrow=0, startcol=vm7_start_col)

    # Get the xlsxwriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Pivot Table with Totals']

    # Define formats
    header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1})
    number_format = workbook.add_format({'num_format': '#,##0.00'})
    total_format = workbook.add_format({'bold': True, 'bg_color': '#FFA07A', 'border': 1, 'num_format': '#,##0'})
    vm7_header_format = workbook.add_format({'bold': True, 'fg_color': '#ADD8E6', 'align': 'center'})  # Light blue for the vm7 header
    percentage_format = workbook.add_format({'num_format': '0.00%'})

    # Apply formatting to existing pivot table
    for col_num, value in enumerate(pivot_table.columns.values):
        worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(col_num, col_num, 18, number_format)

    # Format the 'Grand Total' row
    for col_num in range(len(pivot_table.columns)):
        worksheet.write(len(pivot_table), col_num, pivot_table.iloc[-1, col_num], total_format)

    # Apply vm7 header format and spacing
    worksheet.merge_range(0, vm7_start_col, 0, vm7_start_col + 1, 'VM7 Data', vm7_header_format)

    # Apply number formatting to vm7_data
    for col_num, col_name in enumerate(vm7_data.columns):
        worksheet.set_column(vm7_start_col + col_num, vm7_start_col + col_num, 18, percentage_format)
        