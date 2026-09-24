from uuid import UUID

from sqlalchemy import ForeignKey, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from media_manager.common.models import MediaFileMixin, MediaMixin
from media_manager.database import Base


class Movie(Base, MediaMixin):
    __tablename__ = "movie"
    __table_args__ = (
        UniqueConstraint("external_id", "metadata_provider"),
        UniqueConstraint("slug"),
    )


class MovieFile(Base, MediaFileMixin):
    __tablename__ = "movie_file"
    __table_args__ = (PrimaryKeyConstraint("movie_id", "file_path_suffix"),)

    movie_id: Mapped[UUID] = mapped_column(
        ForeignKey(column="movie.id", ondelete="CASCADE"),
    )



class MovieDownload(Base):
    """
    Links a torrent to the movie it was downloaded for, and the file path
    suffix (version) its file is to be imported as. Created when the download
    starts; the MovieFile row only appears once the file is imported.
    """

    __tablename__ = "movie_download"
    __table_args__ = (PrimaryKeyConstraint("torrent_id", "movie_id"),)

    torrent_id: Mapped[UUID] = mapped_column(
        ForeignKey(column="torrent.id", ondelete="CASCADE"),
    )
    movie_id: Mapped[UUID] = mapped_column(
        ForeignKey(column="movie.id", ondelete="CASCADE"),
        index=True,
    )
    file_path_suffix: Mapped[str]
