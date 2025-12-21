def format_vnd(value):
    if value is None:
        value = 0
    return "{:,.0f} VNĐ".format(value).replace(",", ".")