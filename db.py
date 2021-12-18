import jsonpickle
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Numeric, Boolean, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.types import TypeDecorator, String, Unicode
from datetime import datetime
from drive import get_direct_url
from url_parser import URLParser

# Have absolutely no idea if setting check_same_thread to False is safe,
# nor any idea what it actually does, but it's the only way for SQLAlchemy
# to function in a multi-threaded Flask server (even using Flask-SQLAlchemy).
DB_URI = "sqlite:///app.db?check_same_thread=False"

engine = create_engine(DB_URI)
_SessionFactory = sessionmaker(bind=engine)

Base = declarative_base()

def session_factory():
    Base.metadata.create_all(engine)
    return _SessionFactory()

def flask_session_factory():
    return scoped_session(session_factory)

persistent_session = session_factory()

class JsonType(TypeDecorator):
    impl = Unicode

    def process_bind_param(self, value, engine):
        return str(jsonpickle.encode(value))

    def process_result_value(self, value, engine):
        if value:
            return jsonpickle.decode(value)
        else:
            return None

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    native_id = Column(String, unique=True, nullable=False)
    section_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    prefixes = Column(JsonType())
    prefix = Column(String)
    created_by = Column(String, nullable=False)
    created = Column(DateTime, nullable=False)
    reply_count = Column(Integer, nullable=False)
    view_count = Column(Integer, nullable=False)
    body = Column(String, nullable=False)
    html = Column(String, nullable=False)
    pinned = Column(Boolean, nullable=False)

    first_scraped = Column(DateTime, default=datetime.now)
    last_updated = Column(DateTime, default=datetime.now)

    def get_files(self):
        return persistent_session.query(File).filter_by(post_id=self.id)

    def get_prefix(self, prefix_name):
        return persistent_session.query(Prefix).filter_by(name=prefix_name).first()

    def serialize(self):
        return {
            "id": self.id,
            "native_id": self.native_id,
            "section_id": self.section_id,
            "title": self.title,
            "url": self.url,
            "prefixes": [self.get_prefix(prefix).serialize() for prefix in self.prefixes],
            # "prefix": prefix.serialize() if prefix is not None else None,
            "created_by": self.created_by,
            "created": self.created.timestamp(),
            "reply_count": self.reply_count,
            "view_count": self.view_count,
            "body": self.body,
            "html": self.html,
            "pinned": self.pinned,

            "files": [f.serialize() for f in self.get_files()],

            "first_scraped": self.first_scraped.timestamp(),
            "last_updated": self.last_updated.timestamp()
        }

    def __repr__(self):
        return f"<Post('{self.title}', '{self.get_files().count()} urls')>"

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, nullable=False)
    url = Column(String, nullable=False)
    download_url = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    drive_id = Column(String, nullable=False)
    drive_project_id = Column(String, nullable=False)
    cover = Column(LargeBinary)
    # Only set on files that weren't properly downloaded.
    unknown = Column(Boolean)
    exception = Column(String)
    traceback = Column(String)

    def get_post(self):
        return persistent_session.query(Post).filter_by(id=self.post_id).first()

    def get_hosting_service(self):
        return URLParser().get_hosting_service(self.url)

    def serialize(self):
        hosting_service = self.get_hosting_service()
        return {
            "id": self.id,
            "post_id": self.post_id,
            "url": self.url,
            "download_url": self.download_url,
            "file_name": self.file_name,
            # "drive_id": self.drive_id,
            # "direct_url": get_direct_url(self.drive_id),
            # "cover": self.cover,
            "unknown": self.unknown,

            # "direct_url": get_direct_url(self.drive_id),

            "hosting_service": {
                "name": hosting_service.name,
                "base_url": hosting_service.base_url
            }
        }

    def __repr__(self):
        return f"File<'{self.get_post().title}', '{self.get_hosting_service().name}', '{self.file_name}'>"

class Prefix(Base):
    __tablename__ = "prefix"
    id = Column(Integer, primary_key=True)
    prefix_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    text_color = Column(String, nullable=False)
    bg_color = Column(String, nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "prefix_id": self.prefix_id,
            "name": self.name,
            "text_color": self.text_color,
            "bg_color": self.bg_color
        }

    def __repr__(self):
        return f"Prefix<'{self.name}', '{self.bg_color}'>"
