from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document as LangDocument
from common.config import Config
from common.utils import get_all_documents, load_document

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def build_index():
    docs = []
    for file in get_all_documents():
        text = load_document(file)  # Use the actual function from utils
        docs.append(LangDocument(page_content=text, metadata={"source": file}))
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(Config.VECTOR_STORE)
    return vectorstore


def retrieve_documents(query: str, k=5):
    try:
        vectorstore = FAISS.load_local(
            Config.VECTOR_STORE, embeddings, allow_dangerous_deserialization=True)
        results = vectorstore.similarity_search(query, k=k)
        return results
    except Exception as e:
        # If vector store doesn't exist, build it first
        print(f"Vector store not found, building index: {e}")
        vectorstore = build_index()
        results = vectorstore.similarity_search(query, k=k)
        return results
