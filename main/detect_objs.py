import argparse
import datetime as dt
import logging
from collections import Counter

from models import Detection, Document, Page
from paddleocr import PaddleOCR
from peewee import IntegrityError


def apply_network(ocr):
    """
    Apply the network to images in the given directory. The images
    are converted from PDF to PNG page by page.
    """

    # Get all page images
    Page.select

    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    apply_network("olombendo_output")
