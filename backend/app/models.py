from flask_sqlalchemy import SQLAlchemy
from pgvector.sqlalchemy import Vector
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ready")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chunks = db.relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    embedding = db.Column(Vector(3072).with_variant(db.JSON(), "sqlite"), nullable=False)
    page = db.Column(db.Integer)
    document = db.relationship("Document", back_populates="chunks")
