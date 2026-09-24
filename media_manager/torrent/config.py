from pydantic_settings import BaseSettings


class QbittorrentConfig(BaseSettings):
    host: str = "localhost"
    port: int = 8080
    username: str = "admin"
    password: str = "admin"  # noqa: S105
    # API key (qBittorrent v5.2.0+). When set, it is used instead of username/password.
    api_key: str = ""
    enabled: bool = False

    category_name: str = "MediaManager"
    category_save_path: str = "/data/torrents"  # Default path for container deployments.
    # For host deployments, ensure this path exists in QBittorrent's accessible locations.


class TransmissionConfig(BaseSettings):
    path: str = "/transmission/rpc"
    https_enabled: bool = True
    host: str = "localhost"
    port: int = 9091
    username: str = ""
    password: str = ""
    enabled: bool = False


class SabnzbdConfig(BaseSettings):
    host: str = "localhost"
    port: int = 8080
    api_key: str = ""
    enabled: bool = False
    base_path: str = "/api"


class TorrentConfig(BaseSettings):
    qbittorrent: QbittorrentConfig = QbittorrentConfig()
    transmission: TransmissionConfig = TransmissionConfig()
    sabnzbd: SabnzbdConfig = SabnzbdConfig()
