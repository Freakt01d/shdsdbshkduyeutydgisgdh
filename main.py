import tkinter as tk
from tkinter import filedialog, messagebox
import file_operations

# Define global variables to store file paths
csv_path = ""
xlsx_path = ""
output_dir = ""

def load_file(file_type, entry_widget):
    filetypes = (('CSV files', '*.csv') if file_type == 'csv' else ('Excel files', '*.xlsx'), ('All files', '*.*'))
    filepath = filedialog.askopenfilename(title=f"Open {file_type.upper()} File", filetypes=filetypes)
    if filepath:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filepath)
        if file_type == 'csv':
            global csv_path
            csv_path = filepath
        else:
            global xlsx_path
            xlsx_path = filepath

def select_destination(entry_widget):
    folder_path = filedialog.askdirectory()
    if folder_path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, folder_path)
        global output_dir
        output_dir = folder_path

def process_files():
    global csv_path, xlsx_path, output_dir
    if csv_path and xlsx_path and output_dir:
        try:
            file_operations.file_operations(csv_path, xlsx_path, output_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process the files: {e}")
    else:
        messagebox.showwarning("Warning", "Please select both CSV and XLSX files and the output directory.")

def main_app():
    root = tk.Tk()
    root.title("File Processor")

    tk.Label(root, text="Input CSV File:").grid(row=0, column=0, sticky='w')
    tk.Label(root, text="Input XLSX File:").grid(row=1, column=0, sticky='w')
    tk.Label(root, text="Output Directory:").grid(row=2, column=0, sticky='w')

    csv_entry = tk.Entry(root, width=50)
    csv_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

    xlsx_entry = tk.Entry(root, width=50)
    xlsx_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

    out_entry = tk.Entry(root, width=50)
    out_entry.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

    tk.Button(root, text='Select CSV File', command=lambda: load_file('csv', csv_entry)).grid(row=0, column=2, padx=5, pady=5)
    tk.Button(root, text='Select Xlsx File', command=lambda: load_file('xlsx', xlsx_entry)).grid(row=1, column=2, padx=5, pady=5)
    tk.Button(root, text='Select Destination', command=lambda: select_destination(out_entry)).grid(row=2, column=2, padx=5, pady=5)

    tk.Button(root, text='Process Files', command=process_files).grid(row=3, column=2, padx=5, pady=5)
    root.mainloop()

if __name__ == "__main__":
    main_app()
