import csv
from datetime import datetime
from django.http import StreamingHttpResponse

class Echo:
    def write(self, value): return value

def stream_csv(filename, header, row_iterable):
    pseudo = Echo()
    writer = csv.writer(pseudo)
    def _iter_rows():
        return row_iterable() if callable(row_iterable) else row_iterable

    def gen():
        for row in _iter_rows():
            yield writer.writerow(row)

    resp = StreamingHttpResponse(gen(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp["Cache-Control"] = "no-store"
    return resp

def daterange_filename(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
