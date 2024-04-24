with pd.ExcelWriter(output_dir+'/output_pivot_table.xlsx') as writer:
    pivot_table.to_excel(writer, sheet_name='Pivot Table')
    workbook  = writer.book
    worksheet = writer.sheets['Pivot Table']
    vm7_start_col = len(pivot_table.columns) + 2 

    vm7_data.to_excel(writer, sheet_name='Pivot Table', startrow=1, startcol=vm7_start_col)
    vm7_header_format = workbook.add_format({'bold': True, 'fg_color': '#ADD8E6', 'align': 'center'})  
    percentage_format = workbook.add_format({'num_format': '0.00%'})

    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'bg_color': '#ADD8E6',
        'border': 1
    })

    number_format = workbook.add_format({'num_format': '#,##0'})

    # Set up column labels and formats for vm7_data
    worksheet.merge_range(0, vm7_start_col, 0, vm7_start_col + 1, 'vm7', vm7_header_format)
    worksheet.write(1, vm7_start_col, 'count', workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'}))
    worksheet.write(1, vm7_start_col + 1, 'value', workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'}))

    # Formatting for the pivot_table columns
    for col_num, value in enumerate(pivot_table.columns.values):
        worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(col_num, col_num, 18, number_format)

    # Add grand total
    grand_total_row = len(pivot_table) + 2  # This should be adjusted to your new format
    worksheet.write('A' + str(grand_total_row), 'Grand Total', workbook.add_format({'bold': True,'bg_color':'#ADD8E6'}))
    for i in range(1, len(pivot_table.columns) + 1):
        worksheet.write(grand_total_row - 1, i, pivot_table.iloc[-1, i - 1], workbook.add_format({'bold': True, 'num_format': '#,##0','bg_color':'#ADD8E6'}))

    # Formatting for vm7_data columns
    for col_num in range(2):
        worksheet.set_column(vm7_start_col + col_num, vm7_start_col + col_num, 18, percentage_format)
        