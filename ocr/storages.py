import logging
import mimetypes

from boto3.s3.transfer import TransferConfig
from django.core.files.base import File
from storages.backends.s3boto3 import S3Boto3Storage


class SmallFileS3Storage(S3Boto3Storage):
    """
    < 5 MB  → single PUT with fixed Content‑Length
    ≥ 5 MB  → multipart upload (never streaming‑sig)
    """

    SMALL_LIMIT = 5 * 1024 * 1024
    force_mp = TransferConfig(multipart_threshold=1)  # guarantees MP

    def _save(self, name: str, content: File) -> str:
        logging.warning(
            f"→ SmallFileS3Storage._save({name}) – size={content.size}  "
        )
        # get size without reading entire file for big objects
        content.seek(0, 2)
        size = content.tell()
        content.seek(0)

        if size <= self.SMALL_LIMIT:
            body = content.read()  # bytes → Content‑Length set
            content_type, _ = mimetypes.guess_type(name)
            self.bucket.put_object(
                Key=name,
                Body=body,
                ContentType=content_type,
                ContentLength=size,
                **self.get_object_parameters(name),
            )
            return name

        # large file: force multipart so boto3 never chooses streaming‑sig
        self.transfer_config = self.force_mp
        return super()._save(name, content)
