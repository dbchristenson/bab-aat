# ocr/storage_backends.py

from boto3.s3.transfer import TransferConfig
from storages.backends.s3boto3 import S3Boto3Storage


class MultipartOnlyS3Storage(S3Boto3Storage):
    """
    Every file, no matter how small, is uploaded via multipart.
    Multipart never uses the streaming-signature, so Supabase
    will store *exactly* the bytes you send—no '100000\r\n' prefix.
    """

    def __init__(self, *args, **kwargs):
        # multipart_threshold=1 ⇒ any file >1 byte goes multipart
        # multipart_chunksize can stay at default (5 MB+), but you can tune it
        config = TransferConfig(
            multipart_threshold=1, multipart_chunksize=5 * 1024 * 1024
        )
        kwargs["transfer_config"] = config
        super().__init__(*args, **kwargs)

    def _save(self, name, content):
        # delegate *all* saves to the parent, which will now do multipart
        return super()._save(name, content)
