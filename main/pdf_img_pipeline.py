import argparse
import glob
import os

import pypdfium2 as pdfium
from utils.page_to_img import create_img_and_pad_divisible_by_32

BASE_DIR = "/Users/dbchristenson/Desktop/python/bab-aat/bab-aat"
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")


def check_already_converted(file_path: str, output_dir: str) -> bool:
    pattern = os.path.join(output_dir, f"{file_path[:-2]}*.png")

    return glob.glob(pattern)


def get_pdf_paths(
    dir: str, output_dir: str, absolute_path: bool = False
) -> list[str]:
    """
    Get the paths of all PDF files in the specified directory. When working
    locally on my mac, I already defined a base and data directory. When
    working elsewhere, define the absolute path to the directory containing
    the PDF files.
    """

    if absolute_path:
        pdf_data_dir = dir
    else:
        pdf_data_dir = os.path.join(DATA_DIR, dir)

    pdf_paths = [f for f in os.listdir(pdf_data_dir) if f.endswith(".pdf")]
    assert len(pdf_paths) > 0, f"No PDF files found in {pdf_data_dir}"

    full_pdf_paths = []

    for path in pdf_paths:
        # Check if the PDF defined by the path already has been converted
        file_name = path.split("/")[-1]
        converted = check_already_converted(file_name, output_dir)

        if converted:
            print(f"{file_name} already converted, skipping...")
            continue

        # Join the directory and the path to get the absolute path
        new_path = os.path.join(pdf_data_dir, path)

        # Check if the path is a file
        if os.path.isfile(new_path):
            full_pdf_paths.append(new_path)
        else:
            print(f"{new_path} is not a file")
            continue

    return full_pdf_paths


def convert_pdfs(pdf_paths: list, output_dir: str, scale: int = 4):

    for path in pdf_paths:
        file_name = path.split("/")[-1]
        base_name = file_name.split(".")[0]
        pdf = pdfium.PdfDocument(path)

        """
        print(f"Converting {file_name} to image...")
        print(path)
        print(type(pdf))
        print([p for p in pdf][0].render(scale=scale))
        """

        for i, page in enumerate(pdf):
            # Convert the page to an image
            img = create_img_and_pad_divisible_by_32(page, scale=scale)

            # Save the image
            new_name = f"{base_name}_{i}.png"
            new_path = os.path.join(output_dir, new_name)
            img.save(new_path)

        pdf.close()

    return


def main_pipeline(
    pdf_dir: str, output_dir: str, scale: int = 4, absolute_path: bool = False
):
    os.makedirs(output_dir, exist_ok=True)
    pdf_paths = get_pdf_paths(pdf_dir, output_dir, absolute_path=absolute_path)
    convert_pdfs(pdf_paths, output_dir, scale=scale)

    print("Done converting PDFs to images.")

    return


# /olombendo_src/original_no_ocr/P&ID/Process/
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process PDFs to images.")
    parser.add_argument(
        "--pdf_dir",
        type=str,
        required=True,
        help="Dir with PDFs (relative to DATA_DIR unless --absolute is set).",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directory to save output images.",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=4,
        help="Scale factor for rendering PDF pages (default: 4).",
    )
    parser.add_argument(
        "--absolute",
        action="store_true",
        help="Flag to indicate that pdf_dir is an absolute path.",
    )
    args = parser.parse_args()

    main_pipeline(args.pdf_dir, args.output_dir, args.scale, args.absolute)
