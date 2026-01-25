from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings # <--- Changed
import os

PERSIST_DIRECTORY = "./chroma_db"

def get_vector_store():
    # Use a standard, efficient open-source embedding model running locally
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vector_store = Chroma(
        collection_name="nifty_data",
        embedding_function=embedding_function,
        persist_directory=PERSIST_DIRECTORY
    )
    return vector_store

def add_documents(documents):
    vs = get_vector_store()
    vs.add_documents(documents)
    print(f"Added {len(documents)} chunks to Vector DB.")