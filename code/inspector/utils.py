
# Copied from summarizer.utils

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

