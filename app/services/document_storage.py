import os
from pathlib import Path
from uuid import uuid4


DEFAULT_DOCUMENT_STORAGE_PATH = "storage/documents"


def get_document_storage_root() -> Path:
    """
    Return the root directory used for locally stored documents.

    DOCUMENT_STORAGE_PATH can override the default location,
    which allows tests and deployments to choose their own
    storage root without changing document storage keys.
    """

    return Path(
        os.getenv(
            "DOCUMENT_STORAGE_PATH",
            DEFAULT_DOCUMENT_STORAGE_PATH,
        )
    )


def build_document_storage_key(
    school_id: int,
    original_filename: str,
) -> str:
    """
    Build a unique relative storage key for a school document.

    The database stores this relative key rather than an
    absolute filesystem path so the persistence model is not
    tied to a specific machine or storage backend.
    """

    suffix = Path(original_filename).suffix.lower()

    filename = (
        f"{uuid4().hex}{suffix}"
        if suffix
        else uuid4().hex
    )

    return (
        Path(
            f"school-{school_id}",
            filename,
        )
        .as_posix()
    )


def save_document_bytes(
    storage_key: str,
    content: bytes,
) -> None:
    """
    Persist document bytes beneath the configured storage root.
    """

    storage_root = get_document_storage_root()
    destination = storage_root / storage_key

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(content)


def delete_document_file(
    storage_key: str,
) -> None:
    """
    Remove a stored document if it exists.

    This is used for cleanup when database persistence fails
    after a file has already been written.
    """

    destination = (
        get_document_storage_root()
        / storage_key
    )

    try:
        destination.unlink()
    except FileNotFoundError:
        pass


def read_document_bytes(
    storage_key: str,
) -> bytes:
    """
    Read a stored document from the configured document storage.

    The storage key is resolved relative to the same root used
    when document files are saved.
    """

    storage_root = get_document_storage_root()
    source = storage_root / storage_key

    if not source.is_file():
        raise FileNotFoundError(
            f"Stored document not found: {storage_key}"
        )

    return source.read_bytes()
