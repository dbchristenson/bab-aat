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


def _format_bbox_to_string(polygon_coords: list) -> str:
    """
    Converts a list of coordinate pairs (polygon) to a string.
    Example: [[x1,y1],[x2,y2],[x3,y3]] -> "x1,y1;x2,y2;x3,y3"
    Handles None or non-list inputs gracefully.
    """
    if not isinstance(polygon_coords, list):
        return str(polygon_coords) if polygon_coords is not None else ""

    if not polygon_coords:  # Handles empty list
        return ""

    # Check if it's a list of lists (pairs of coordinates)
    if not all(
        isinstance(pair, list) and len(pair) == 2 for pair in polygon_coords
    ):
        # Fallback for unexpected format within the list,
        # though ideally the data structure is consistent.
        # This will convert simple lists like [1,2,3,4] to "1,2,3,4"
        # or just stringify if elements are not numbers.
        return ",".join(map(str, polygon_coords))

    # Format: "x1,y1;x2,y2;..."
    return ";".join([f"{coord[0]},{coord[1]}" for coord in polygon_coords])


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
        df = df.with_columns(
            pl.col("bbox")
            .map_elements(_format_bbox_to_string, return_dtype=pl.String)
            .alias("bbox")
        )

    if "created_at" in df.columns:
        # Check if the column is of a datetime type and has timezone info
        if df["created_at"].dtype in [
            pl.Datetime,
            pl.Datetime("us"),
            pl.Datetime("ns"),
            pl.Datetime("ms"),
        ]:
            df = df.with_columns(
                pl.col("created_at")
                .dt.replace_time_zone(None)
                .alias("created_at")
            )

    df = df.rename(_EXCEL_COLUMN_NAMES_MAP)

    excel_buffer = io.BytesIO()
    df.write_excel(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer.getvalue()
