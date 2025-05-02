from boto3.s3.transfer import TransferConfig
from storages.backends.s3boto3 import S3Boto3Storage

config = TransferConfig(
    multipart_threshold=25 * 1024 * 1024,  # 25 MiB
    multipart_chunksize=25 * 1024 * 1024,  # 25 MiB
    use_threads=True,
)


class ChunkedS3Storage(S3Boto3Storage):
    """
    Subclass that always uses our 25MiB TransferConfig. We are injecting
    the transfer_config into the S3Boto3Storage class to ensure that
    large files are uploaded in chunks to avoid EntityTooLarge errors.
    """

    def __init__(self, *args, **kwargs):
        kwargs["transfer_config"] = config
        super().__init__(*args, **kwargs)
