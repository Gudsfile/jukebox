def table(headers, rows, indexed=False):
    if indexed:
        headers = ["#"] + headers
        rows = [[i + 1] + list(row) for i, row in enumerate(rows)]

    cols = list(zip(headers, *rows))
    widths = [max(len(str(x)) for x in col) for col in cols]

    def fmt(row):
        return "  ".join(f"{str(val):<{widths[i]}}" for i, val in enumerate(row))

    return "\n".join([fmt(headers), *map(fmt, rows)])
