import base64
import binascii
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.models.models import Installation, InstallationPhoto, User

MEDIA_ROOT = Path(settings.MEDIA_DIR).resolve()
PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def _image_type(head: bytes) -> Optional[str]:
    """Identify the file by its first bytes, not by the name or content type the sender claims."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(PNG_HEADER):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _folder(installation_id: int) -> Path:
    folder = MEDIA_ROOT / "installations" / str(installation_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolve_file(relative_path: str) -> Path:
    """Turn a stored relative path into a real file, refusing anything outside the media folder."""
    path = (MEDIA_ROOT / relative_path).resolve()
    if MEDIA_ROOT not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return path


def _clean_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name)[:255]


class InstallationProofService:
    @staticmethod
    async def save_photo(
        db: Session, installation: Installation, upload: UploadFile, caption: str, user: User
    ) -> InstallationPhoto:
        if installation.status == "Completed":
            raise HTTPException(status_code=400, detail="This installation is complete, so photos can no longer be added.")

        data = await upload.read(settings.MAX_PHOTO_BYTES + 1)
        if not data:
            raise HTTPException(status_code=400, detail="The file is empty.")
        if len(data) > settings.MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"The photo is larger than {settings.MAX_PHOTO_BYTES // (1024 * 1024)} MB. Please send a smaller one.",
            )
        kind = _image_type(data[:16])
        if not kind:
            raise HTTPException(status_code=400, detail="Only JPEG, PNG or WebP photos are accepted.")

        name = f"{uuid.uuid4().hex}.{kind}"
        (_folder(installation.id) / name).write_bytes(data)
        photo = InstallationPhoto(
            installation_id=installation.id,
            file_path=f"installations/{installation.id}/{name}",
            original_name=_clean_name(upload.filename),
            caption=(caption or "").strip()[:255] or None,
            uploaded_by=user.id,
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        return photo

    @staticmethod
    def delete_photo(db: Session, installation: Installation, photo_id: int) -> None:
        if installation.status == "Completed":
            raise HTTPException(status_code=400, detail="This installation is complete, so its proof can no longer change.")
        photo = (
            db.query(InstallationPhoto)
            .filter(InstallationPhoto.id == photo_id, InstallationPhoto.installation_id == installation.id)
            .first()
        )
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found.")
        try:
            (MEDIA_ROOT / photo.file_path).unlink(missing_ok=True)
        except OSError:
            pass
        db.delete(photo)
        db.commit()

    @staticmethod
    def save_signature(db: Session, installation: Installation, signed_by: str, data_url: str) -> Installation:
        if installation.status == "Completed":
            raise HTTPException(status_code=400, detail="This installation is complete, so its signature can no longer change.")
        prefix = "data:image/png;base64,"
        if not data_url.startswith(prefix):
            raise HTTPException(status_code=400, detail="The signature must be a PNG image.")
        try:
            data = base64.b64decode(data_url[len(prefix):], validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail="The signature image could not be read.")
        if len(data) > settings.MAX_SIGNATURE_BYTES:
            raise HTTPException(status_code=413, detail="The signature image is too large.")
        if not data.startswith(PNG_HEADER):
            raise HTTPException(status_code=400, detail="The signature must be a PNG image.")

        (_folder(installation.id) / "signature.png").write_bytes(data)
        installation.signature_path = f"installations/{installation.id}/signature.png"
        installation.signed_by_name = signed_by.strip()
        installation.signed_at = datetime.utcnow()
        db.commit()
        db.refresh(installation)
        return installation

    @staticmethod
    def ensure_proof(db: Session, installation: Installation) -> None:
        """A job is only complete once there are photos of the finished roof and the homeowner has signed."""
        missing = []
        photo_count = db.query(InstallationPhoto).filter(InstallationPhoto.installation_id == installation.id).count()
        if photo_count < settings.MIN_INSTALLATION_PHOTOS:
            needed = settings.MIN_INSTALLATION_PHOTOS
            missing.append(f"at least {needed} photo{'s' if needed != 1 else ''} of the finished roof ({photo_count} added)")
        if not installation.signature_path or not installation.signed_by_name:
            missing.append("the homeowner's signature")
        if missing:
            raise HTTPException(
                status_code=400,
                detail="Cannot complete the job yet. It still needs " + " and ".join(missing) + ".",
            )
