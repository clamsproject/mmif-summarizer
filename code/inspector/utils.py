import json


def pretty_json(json_obj: dict):
    return '<pre>'+json.dumps(json_obj, indent=2)+'</pre>'


def timestamp(milliseconds: int, format='hh:mm:ss'):
    # sometimes the milliseconds are not a usable float
    if milliseconds in (None, -1):
        return 'nil'
    milliseconds = int(milliseconds)
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    ms = milliseconds % 1000
    s = seconds % 60
    m = minutes % 60
    if format == 'hh:mm:ss:mmm':
        return f'{hours}:{m:02d}:{s:02d}.{ms:03d}'
    elif format == 'hh:mm:ss':
        return f'{hours}:{m:02d}:{s:02d}'
    elif format == 'mm:ss':
        return f'{m:02d}:{s:02d}'
    elif format == 'mm:ss:mmm':
        return f'{m:02d}:{s:02d}.{ms:03d}'
    else:
        return f'{hours}:{m:02d}:{s:02d}.{ms:03d}'



# TODO: this may be deprecated, make it more general in case we use it again
def sorted_pairs(d: dict):
    """Return the dictionary as a list of sorted <key, value> where the sorting
    is done on the 'duration' property of the values in the dictionary."""
    sort_function = lambda item: item[1]['duration']
    return [(k, v) for k, v in 
            sorted(d.items(), key=sort_function, reverse=True)]
