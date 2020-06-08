import csv
from io import StringIO
import json


def csv_and_mapping_create(contacts, fields):
    """Helper function that takes a dictionary of contacts and CallHub field name -> id mappings and creates
    a CSV in-memory that CallHub will accept.
    Returns:
        csv_file (``file``): CSV file for upload to CallHub
        mapping (``dict``): A mapping of CallHub field IDs to CSV column indexes
        >>> {"0": "0", "1": "1"}
        """
    csv_file = StringIO()

    # Create CSV (stored in memory as StringIO)
    for contact in contacts:
        new_row = [""] * (len(fields) + 1)
        for field in fields:
            if contact.get(field):
                new_row[fields[field]] = contact[field]
        csv.writer(csv_file).writerow(new_row)

    # Create mapping for CallHub upload
    mapping = {}
    for field in fields:
        mapping[fields[field]] = str(fields[field])
    mapping = json.dumps(mapping).replace("'", "\"")

    return csv_file.getvalue(), mapping
