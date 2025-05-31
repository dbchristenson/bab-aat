import os

import modal

PADDLE_OCR_MODELS_ROOT_IN_VOLUME = "/ocr_model_cache_vol"

volume = modal.Volume.from_name("paddleocr-cache-v5", create_if_missing=True)
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
    "ccache",
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

with inference_image.imports():
    from paddleocr import PaddleOCR

_ocr_instances = {}

MODEL_COMPONENT_CONFIG = {
    "text_detection": {
        "name_key": "text_detection_model_name",
        "dir_key": "text_detection_model_dir",
        "use_flag": None,  # Core component, always used
    },
    "text_recognition": {
        "name_key": "text_recognition_model_name",
        "dir_key": "text_recognition_model_dir",
        "use_flag": None,  # Core component, always used
    },
    "textline_orientation": {
        "name_key": "textline_orientation_model_name",
        "dir_key": "textline_orientation_model_dir",
        "use_flag": "use_textline_orientation",
    },
    "doc_orientation_classify": {
        "name_key": "doc_orientation_classify_model_name",
        "dir_key": "doc_orientation_classify_model_dir",
        "use_flag": "use_doc_orientation_classify",
    },
    "doc_unwarping": {
        "name_key": "doc_unwarping_model_name",
        "dir_key": "doc_unwarping_model_dir",
        "use_flag": "use_doc_unwarping",
    },
}


def _prepare_model_paths_and_params(
    config_id: str, user_ocr_params: dict
) -> dict:
    """
    Helper to construct model directory paths in the volume and prepare
    parameters for PaddleOCR initialization.
    It creates directories if they don't exist.
    """
    # Work on a copy to avoid modifying the input dict
    paddle_init_params = user_ocr_params.copy()

    config_specific_base_path = os.path.join(
        PADDLE_OCR_MODELS_ROOT_IN_VOLUME, config_id
    )

    for component, details in MODEL_COMPONENT_CONFIG.items():
        model_name_config_key = details["name_key"]
        model_dir_paddle_key = details["dir_key"]
        use_component_flag_key = details["use_flag"]

        component_enabled_by_flag = True
        if use_component_flag_key:
            # If use_flag is present and False, component is disabled
            # If use_flag is not present, default behavior of PaddleOCR applies
            # (some are True by default, some False).
            # We only set up cached dir if user enables or it's core.
            if paddle_init_params.get(use_component_flag_key, True) is False:
                component_enabled_by_flag = False

        # If user provided a specific model name for this component
        if model_name_config_key in paddle_init_params:
            model_folder_name = paddle_init_params.pop(model_name_config_key)

            if component_enabled_by_flag:
                model_full_path = os.path.join(
                    config_specific_base_path, model_folder_name
                )
                # This is the "helper function to create directories"
                os.makedirs(model_full_path, exist_ok=True)
                paddle_init_params[model_dir_paddle_key] = model_full_path
            # If component_enabled_by_flag is F, we've popped the *_model_name,
            # and we don't set the corresponding *_model_dir. PaddleOCR will
            # respect the use_flag (e.g., use_textline_orientation=False).

    # Default to GPU if not specified
    if (
        "use_gpu" not in paddle_init_params
        and "device" not in paddle_init_params
    ):
        paddle_init_params["use_gpu"] = True  # For older PaddleOCR param style
        # For newer "device" param: paddle_init_params["device"] = "gpu:0"

    # Reduce PaddleOCR's default verbosity
    if "show_log" not in paddle_init_params:
        paddle_init_params["show_log"] = False

    return paddle_init_params


def get_or_create_ocr_instance(config_id: str, user_ocr_params: dict):
    """
    Runtime function to get/create a PaddleOCR instance.
    Loads models from pre-populated volume.
    """

    if config_id in _ocr_instances:
        return _ocr_instances[config_id]

    # Prepare paths and parameters
    paddle_init_params = _prepare_model_paths_and_params(
        config_id, user_ocr_params
    )

    # This will load models from the paths specified in paddle_init_params,
    # which should have been populated by the @app.build step.
    ocr_instance = PaddleOCR(**paddle_init_params)

    _ocr_instances[config_id] = ocr_instance
    return ocr_instance


KNOWN_OCR_CONFIGS_TO_PREWARM = {
    1: {
        "lang": "en",
        "enable_hpi": False,
        "text_det_limit_type": "max",
        "text_det_unclip_ratio": 2,
        "text_det_limit_side_len": 2880,
        "use_textline_orientation": True,
        "text_detection_model_name": "PP-OCRv5_mobile_det",
        "text_recognition_model_name": "PP-OCRv5_mobile_rec",
    }
}


@app.build(volumes={PADDLE_OCR_MODELS_ROOT_IN_VOLUME: volume})
def preload_models():
    """
    This function runs when you deploy the Modal app.
    It prepares paths and then initializes PaddleOCR for known configs,
    which triggers downloads to the persistent volume if models aren't there.
    This is the "helper function to actually download the models".
    """

    print(f"Starting pre-loading of models into volume: {volume.object_id}")
    for cid, params in KNOWN_OCR_CONFIGS_TO_PREWARM.items():
        print(f"Pre-loading models for config_id: {cid}...")
        try:
            paddle_init_params = _prepare_model_paths_and_params(cid, params)

            PaddleOCR(**paddle_init_params)
        except Exception as e:
            print(f"Error pre-loading models for config_id {cid}: {e}")
            # Optionally, decide if an error here should fail the build
    print("Finished pre-loading models.")


@app.function(
    image=inference_image,
    gpu="T4",
    retries=3,
    volumes={"/my_vol": modal.Volume.from_name("paddle-3.0.0")},
)
def ocr_inference(im_numpy, config_id: int, paddle_config: dict):
    """
    PaddleOCR inference function.

    Args:
        im_numpy (numpy.ndarray): Input image in numpy format.
        config_id (int): Identifier for the OCR configuration to use.
        paddle_config (dict): Configuration options for PaddleOCR.

    Returns:
        list: List of OCR results.
    """

    ocr = get_or_create_ocr_instance(
        config_id=paddle_config.get("config_id", "default"),
        user_ocr_params=paddle_config,
    )
    results = ocr.predict(im_numpy)

    return results
