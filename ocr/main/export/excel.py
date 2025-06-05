import io

import polars as pl

FIELDS_TO_EXPORT = [
    "document__id",
    "document__document_number",
    "page_number",
    "text",
    "bbox",
    "equipment_tag",
    "created_at",
]

_EXCEL_COLUMN_NAMES_MAP = {
    "document__id": "Document ID",
    "document__document_number": "Document Number",
    "page_number": "Page Number",
    "text": "Tag Text",
    "bbox": "Location (Bounding Box Coordinates)",
    "equipment_tag": "Equipment Tag",
    "created_at": "Created At",
}


def export_document_tags_to_excel(data_object: dict) -> bytes:
    """Exports tags for document(s) to an in-memory Excel file.

    The structure of the Excel file will be a denormalized table that
    focuses on relaying information about the tags of the documents.
    The table will include the following columns:
        - Document ID
        - Document Number
        - Page Number
        - Tag Text
        - Location (Bounding Box Coordinates)
        - Equipment Tag
        - Created At

    The goal of the table is to have all relevant tags be the unique rows
    while the document and page information is repeated for each tag.
    """
    tags_data = data_object.get("tags") or []

    df = pl.DataFrame(data=tags_data, schema=FIELDS_TO_EXPORT, strict=False)

    if "bbox" in df.columns:
        df = df.with_columns(pl.col("bbox").cast(pl.String))

    df = df.rename(_EXCEL_COLUMN_NAMES_MAP)

    excel_buffer = io.BytesIO()
    df.write_excel(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer.getvalue()
