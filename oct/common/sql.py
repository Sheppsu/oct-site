def parse_sql_row(row: str, transformers):
    if not row.startswith("(") or not row.endswith(")"):
        raise ValueError("Invalid row given")
    row = row[1:-1]+","

    data = []
    min_i = 0
    inside_string = False
    for i in range(len(row)):
        if row[i] == "," and not inside_string:
            value = row[min_i:i]
            if value.startswith('"'):
                value = value[1:-1]
            data.append(value.replace('""', '"'))
            min_i = i+1
        elif row[i] == '"':
            inside_string = not inside_string
            
    if len(transformers) != len(data):
        print(data)
        raise ValueError("Number of transformers does not match up with the number of columns")
            
    return tuple(map(lambda item: item[1] if transformers[item[0]] == str or item[1] == "" else transformers[item[0]](item[1]), enumerate(data)))
