from app.config import Settings
from app.storage.base import StorageAdapter
from app.storage.local import LocalStorageAdapter
from app.storage.supabase import SupabaseStorageAdapter


def create_storage_adapter(settings: Settings) -> StorageAdapter:
    if settings.data_backend == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError(
                "Supabase storage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
            )
        return SupabaseStorageAdapter(
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.supabase_storage_bucket,
        )
    return LocalStorageAdapter(settings.local_storage_path)

