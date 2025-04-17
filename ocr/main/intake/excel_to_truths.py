import datetime as dt
import logging
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babaatsite.settings")
django.setup()

import pandas as pd  # noqa E402

from ocr.main.utils.loggers import basic_logging  # noqa E402
from ocr.models import Document, Truth  # noqa E402

basic_logging(__name__)


# Okay to run this script its kinda complicated but here is what to do.
# From your terminal at the root of the project run the following command:
# python -m ocr.main.intake.excel_to_truths

# If that doesn't work then set the environment variable manually in terminal:
# set DJANGO_SETTINGS_MODULE=bab_aat.settings


# Kraken
def et_kraken(spreadsheet_path: str) -> pd.DataFrame:
    """
    Load the spreadsheet from the given path and extract the relevant columns.

    Args:
        spreadsheet_path (str): Path to the spreadsheet file.

    Returns:
        pd.DataFrame: DataFrame containing the extracted columns, cleaned.
    """
    df = pd.read_excel(spreadsheet_path)

    # Note the space in "Tag Number ", this is intentional
    target_columns = ["Document Number", "Tag Number "]
    new_columns = ["document_number", "tag_number"]

    new_df = df[target_columns].copy(deep=True)
    new_df.columns = new_columns

    # Remove rows with missing values
    new_df = new_df.dropna()

    # Remove rows with UNTAGGED in the tag_number string
    new_df = new_df[
        new_df["tag_number"].contains("UNTAGGED") == False  # noqa E712
    ]

    return new_df


def load_kraken(kraken_df: pd.DataFrame) -> None:
    """
    Take a DataFrame and load it into the database.

    Args:
        kraken_df (pd.DataFrame): DataFrame containing the data to load.
    """

    for _, row in kraken_df.iterrows():
        # Create a new Truth object
        truth = Truth(
            document=Document.objects.filter(
                document_number=row["document_number"]
            ).first(),
            document_number=row["document_number"],
            text=row["tag_number"],
            created_at=dt.datetime.now(),
        )
        # Save the object to the database
        truth.save()

    logging.info(f"Loaded {len(kraken_df)} truths into the database.")

    return


Truth.objects.all().delete()

spreadsheet_path = "C:\\Users\\User\\Downloads\\OVERALL BAE P&ID_250213.xlsx"

kraken_df = et_kraken(spreadsheet_path)
load_kraken(kraken_df)
