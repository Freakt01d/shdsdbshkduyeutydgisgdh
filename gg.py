import pandas as pd
import xlsxwriter

# Sample DataFrame
data = {
    'Category': ['A', 'B', 'A', 'B', 'A', 'B'],
    'Value': [10, 20, 30, 40, 50, 60]
}
df = pd.DataFrame(data)

# Create a pivot table
pivot_table = df.pivot_table(index='Category', values='Value', aggfunc='sum')

# Define starting row for pivot table
start_row = 0

# Write the pivot table to an Excel file and format it
output_file = "pivot_table.xlsx"
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    workbook = writer.book
    worksheet = workbook.add_worksheet('Pivot Table')

    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'bg_color': '#ADD8E6',
        'border': 1
    })
    cell_format = workbook.add_format({'border': 1})

    # Write the pivot table headers
    for col_num, value in enumerate(pivot_table.columns.values):
        worksheet.write(start_row, col_num + 1, value, header_format)

    # Write the pivot table data with border formatting
    num_rows, num_cols = pivot_table.shape
    for row in range(start_row + 1, start_row + num_rows + 1):
        for col in range(1, num_cols + 1):
            cell_value = pivot_table.iloc[row - start_row - 1, col - 1]
            worksheet.write(row, col, cell_value, cell_format)

    # Optionally adjust the column widths
    for col_num in range(num_cols):
        worksheet.set_column(col_num + 1, col_num + 1, 20)  # Adjust width as needed

print(f"Pivot table written to '{output_file}'.")
