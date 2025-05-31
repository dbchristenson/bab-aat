import modal

PADDLE_MODEL_DIR = "/paddle_models"

volume = modal.Volume.from_name("paddle-3.0.0", create_if_missing=True)
app = modal.App("modal-ocr")

# Constants for image
APT_PKGS = [
    "build-essential",
    "libglib2.0-0",
    "libgl1",
    "libsm6",
    "libxrender1",
    "poppler-utils",
    "libmagic1",
    "libmagic-dev",
    "curl",
]
UV_INSTALL_SETUPTOOLS = "uv pip install --system --compile-bytecode setuptools"
UV_ADD_PP = "uv pip install --system --compile-bytecode paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/"  # noqa: E501
UV_ADD_PPOCR = (
    "uv pip install --system --compile-bytecode paddleocr==3.0.0"  # noqa: E501
)

inference_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(*APT_PKGS)
    .pip_install("uv")
    .run_commands(UV_INSTALL_SETUPTOOLS)
    .run_commands(UV_ADD_PP)
    .run_commands(UV_ADD_PPOCR)
)


@app.function(
    image=inference_image,
    gpu="T4",
    retries=3,
    volumes={"/my_vol": modal.Volume.from_name("paddle-3.0.0")},
)
def ocr_inference(im_numpy, paddle_config: dict):
    """
    PaddleOCR inference function.

    Args:
        im_numpy (numpy.ndarray): Input image in numpy format.
        paddle_config (dict): Configuration options for PaddleOCR.

    Returns:
        list: List of OCR results.
    """
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(**paddle_config)
    results = ocr.predict(im_numpy)

    return results
