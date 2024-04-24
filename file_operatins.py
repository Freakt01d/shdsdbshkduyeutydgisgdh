# Create a new DataFrame with instrument types and sub-products listed in a single column
dropdown_list = []
for instrument_type, group in pivot_table.groupby('INSTRUMENT_TYPE'):
    dropdown_list.append(instrument_type)
    dropdown_list.extend(['  ' + sub_product for sub_product in group['PRODUCT_STRUCTURE_TYPE'].unique()])

# Export the pivot table to Excel with the dropdown list
output_file = 'pivot_table_with_dropdown.xlsx'
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    # Create a DataFrame with dropdown list
    dropdown_df = pd.DataFrame({'Dropdown': dropdown_list})
    dropdown_df.to_excel(writer, sheet_name='Dropdown List', index=False)

    # Write the pivot table to a separate sheet
    pivot_table.to_excel(writer, sheet_name='Pivot Table', index=False)