import pickle
import os

# create a markdown table
def create_comparison_table(pairs, column_names=['Original Text', 'Enhanced Text', 'Enhanced Text 2']):
    # Check if any pair has 3 elements
    has_third_column = any(len(pair) == 3 for pair in pairs)
    
    # Create table header
    if has_third_column:
        table = f"| {column_names[0]} | {column_names[1]} | {column_names[2]} |\n|---------------|-----------------|----------------|\n"
    else:
        table = f"| {column_names[0]} | {column_names[1]} |\n|---------------|---------------|\n"
    
    # Add rows to the table
    for pair in pairs:
        x = pair[0].replace('|', '\\|').replace('\n', '<br>')
        y1 = pair[1].replace('|', '\\|').replace('\n', '<br>')
        
        if has_third_column:
            y2 = pair[2].replace('|', '\\|').replace('\n', '<br>') if len(pair) == 3 else ''
            table += f"| {x} | {y1} | {y2} |\n"
        else:
            table += f"| {x} | {y1} |\n"
    
    return table