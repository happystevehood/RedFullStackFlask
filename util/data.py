import csv
import os
from pathlib import Path

#
# data gonna be structured as below 
#
# static - csv 	- input
#				- generic
#		 - pdf 	- generic
#				- comp
#		 - png	- generic
#				- comp


CSV_INPUT_DIR   = Path('static') / 'csv' / 'input'
CSV_GENERIC_DIR = Path('static') / 'csv' / 'generic' 
PDF_COMP_DIR    = Path('static') / 'pdf' / 'comp' 
PDF_GENERIC_DIR = Path('static') / 'pdf' / 'generic' 
PNG_COMP_DIR    = Path('static') / 'png' / 'comp'
PNG_GENERIC_DIR = Path('static') / 'png' / 'generic' 



def init_filepaths(dummy):

    print(CSV_INPUT_DIR)

    return True


# helper function
def remove_files_from_directory(directory):
    """Removes all files within the specified directory, but leaves the directory untouched."""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)


def delete_generated_files():
    """Removes all data files generated here included competitor files"""
    remove_files_from_directory(CSV_GENERIC_DIR);
    remove_files_from_directory(PDF_COMP_DIR); 
    remove_files_from_directory(PDF_GENERIC_DIR); 
    remove_files_from_directory(PNG_COMP_DIR); 
    remove_files_from_directory(PNG_GENERIC_DIR);

def delete_competitor_files():
    """Removes all competitor data files generated here"""
    remove_files_from_directory(PDF_COMP_DIR); 
    remove_files_from_directory(PNG_COMP_DIR); 