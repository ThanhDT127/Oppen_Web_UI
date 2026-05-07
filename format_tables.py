import sys
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    out_lines = []
    
    table_lines = []
    
    def format_table(t_lines):
        # if the table is just single column or doesn't have structure, return as is
        if len(t_lines) < 3 or '---' not in t_lines[1]:
            return t_lines
            
        header = [c.strip() for c in t_lines[0].split('|')[1:-1]]
        if not header:
            return t_lines
            
        if header[0].upper() == 'STT' or header[0] == '#':
            # It already has STT, skip modification but align it
            pass
        else:
            # Need to insert STT
            for i in range(len(t_lines)):
                if i == 0:
                    t_lines[i] = '| STT ' + t_lines[i]
                elif i == 1:
                    t_lines[i] = '| --- ' + t_lines[i]
                else:
                    t_lines[i] = f'| {i-1:02d}  ' + t_lines[i]

        # Re-parse to align
        parsed_rows = []
        for r_line in t_lines:
            cols = [c.strip() for c in r_line.split('|')[1:-1]]
            parsed_rows.append(cols)
            
        if not parsed_rows:
            return t_lines

        widths = [len(c) for c in parsed_rows[0]]
        for row in parsed_rows:
            for i, c in enumerate(row):
                if '-' in c and not any(ch.isalnum() for ch in c):
                    continue # skip separator row for width calc
                if i < len(widths):
                    widths[i] = max(widths[i], len(c))
                else:
                    widths.append(len(c))
                    
        formatted = []
        for i, row in enumerate(parsed_rows):
            if i == 1:
                # separator
                sep = "| " + " | ".join('-' * w for w in widths) + " |"
                formatted.append(sep)
            else:
                formatted_cols = []
                for j, c in enumerate(row):
                    if j < len(widths):
                        formatted_cols.append(c.ljust(widths[j]))
                    else:
                        formatted_cols.append(c)
                formatted.append("| " + " | ".join(formatted_cols) + " |")
        
        return formatted

    for line in lines:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            table_lines.append(line)
        else:
            if len(table_lines) > 0:
                out_lines.extend(format_table(table_lines))
                table_lines = []
            out_lines.append(line)
            
    if len(table_lines) > 0:
        out_lines.extend(format_table(table_lines))

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
        
    print(f"Processed {filepath}")

for arg in sys.argv[1:]:
    process_file(arg)
