from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import IO


@dataclass
class UploadResult:
    object_key: str
    object_url: str
    etag: str | None = None
    file_size: int | None = None


class ObjectStorageClient(ABC):
    @abstractmethod
    def upload_fileobj(self, fileobj: IO[bytes], object_key: str, content_type: str = "video/mp4") -> UploadResult:
        ...

    @abstractmethod
    def get_public_url(self, object_key: str) -> str:
        ...
