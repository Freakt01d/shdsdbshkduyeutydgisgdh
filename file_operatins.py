# Create a pivot table with multi-level index
new_pivot_table = pd.pivot_table(filtered_noncustomer,
                                 index=['INSTRUMENT_TYPE', 'PRODUCT_STRUCTURE_TYPE'],
                                 values=['ABS_EXCHANGEDAMOUNT_USD', 'COUNTERP_TRADEPARTYID'],
                                 aggfunc={'ABS_EXCHANGEDAMOUNT_USD': np.sum, 'COUNTERP_TRADEPARTYID': 'count'},
                                 fill_value=0)

# Write to Excel, with the pivot table placed 10 rows below the previous one
output_file = 'output_pivot_table_with_vm7.xlsx'
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    # Assume the previous pivot table is saved in this writer session
    worksheet = writer.sheets['Pivot Table with Totals']
    start_row = 10 + len(pivot_table.index) + 10  # calculate the starting row

    # Save the new pivot table with multi-level index
    new_pivot_table.to_excel(writer, sheet_name='Pivot Table with Totals', startrow=start_row)

    # Get the workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Pivot Table with Totals']

    # Set up the pivot table styles
    pivot_table_range = 'A' + str(start_row + 1)
    pivot_table_end = 'B' + str(start_row + len(new_pivot_table) + 1)

    pivot_table_format = {
        'type': 'dropdown',
        'source': ['Bond', 'Stock', 'Other'],  # Replace with your instrument types
    }

    # Add drop-down menus to the first level of the index
    worksheet.add_data_validation(pivot_table_range, pivot_table_format)
    worksheet.add_data_validation(pivot_table_end, pivot_table_format)

    # Autofit columns for better visibility
    for col in range(1, len(new_pivot_table.columns) + 1):
        worksheet.set_column(col, col, width=18)