import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from flask_dance.contrib.github import make_github_blueprint, github

load_dotenv()

db = SQLAlchemy()
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

es = Elasticsearch(
    os.getenv("ELASTICSEARCH_URL"),
    api_key=os.getenv("ELASTICSEARCH_API_KEY"),
)

def create_doc_index(index_name):
    # Define index mapping with dense_vector field and organisation_id
    mapping = {
        "mappings": {
            "properties": {
                "organisation_id": {"type": "keyword"},  # Add this
                "text": {"type": "text"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }

    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body=mapping)
        print(f"Index '{index_name}' created successfully.")
    else:
        print(f"Index '{index_name}' already exists.")

def create_rag_index(index_name):
    mapping = {
        "mappings": {
            "properties": {
                "organisation_id": {"type": "keyword"}, # Filter for organizations
                "question_id": {"type": "keyword"},     # Filter for question id
                "question": {"type": "text"},           # Store questions
                "answer": {"type": "text"},             # Store answers
                "embedding": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }

    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body=mapping)
        print(f"Index '{index_name}' created.")
    else:
        print(f"Index '{index_name}' already exists.")

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['UPLOAD_FOLDER'] = './uploaded_files'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit
    app.secret_key = 'supersecretkey'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #github

    os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2")
    os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT")
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")

    db.init_app(app)

    from .routes.user import user_bpt
    from .routes.moderator import moderator_bpt
    from .routes.organization import organization_bpt
    from .routes.up_down_votes import votes_bpt
    from .routes.question_answer import QA_bpt
    from .routes.other import other_bpt

    app.register_blueprint(user_bpt, url_prefix='/')
    app.register_blueprint(moderator_bpt, url_prefix='/')
    app.register_blueprint(organization_bpt,url_prefix='/')
    app.register_blueprint(votes_bpt,url_prefix='/')
    app.register_blueprint(QA_bpt,url_prefix='/')
    app.register_blueprint(other_bpt,url_prefix='/')

    github_blueprint =  make_github_blueprint(client_id="Ov23liKvW6x8kR3KgYjv",client_secret='e5b107533855dcc73beac7b3cae13c76bb601d96')
    app.register_blueprint(github_blueprint,url_prefix='/github_login')

    create_doc_index(os.getenv("DOC_INDEX_NAME"))
    create_rag_index(os.getenv("QA_INDEX_NAME"))

    with app.app_context():
        db.create_all()

    return app