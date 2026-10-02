from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ready")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    chunks = db.relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON, nullable=False)
    page = db.Column(db.Integer)
    document = db.relationship("Document", back_populates="chunks")
