import pandas as pd
import xlsxwriter

# Example DataFrame
data = pd.DataFrame({
    'Data': [10, 20, 30, 40],
    'More Data': [100, 200, 300, 400]
}, index=['First', 'Second', 'Third', 'Fourth'])

# Create a writer object and specify the engine
with pd.ExcelWriter('formatted_pivot.xlsx', engine='xlsxwriter') as writer:
    workbook = writer.book
    worksheet = workbook.add_worksheet('Sheet1')
    writer.sheets['Sheet1'] = worksheet

    # Write the DataFrame to Excel without the index
    data.to_excel(writer, sheet_name='Sheet1', startrow=1, index=False)

    # Define format for the index
    index_format = workbook.add_format({
        'bold': True,
        'bg_color': '#FFFF00',  # Yellow background
        'border': 1
    })

    # Manually write the index
    for idx, value in enumerate(data.index):
        worksheet.write(idx + 1, 0, value, index_format)  # Writing index values in the first column with formatting

    # Optionally format columns and data if needed
    worksheet.set_column('A:A', 15, index_format)  # Set the width of the column with index

# Note that the rest of the columns can be auto-formatted by defining additional formats and applying them as needed.
