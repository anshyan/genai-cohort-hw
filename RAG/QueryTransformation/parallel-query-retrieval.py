from pathlib import Path
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

# Set your Google API key
os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

pdf_path = Path(__file__).parent.parent / "DataSource" / "Embeddings & vector stores.pdf"

# Initialize Qdrant client
client = QdrantClient(url="http://localhost:6333")
collection_name = "pdf_embeddings"

# Initialize Gemini embeddings
vector_embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001"
)

try:
    # Try to get collection info - if it exists
    collection_info = client.get_collection(collection_name)
    print(f"Collection '{collection_name}' already exists")
    
    # Use existing collection
    qdrant = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=vector_embedding_model,
    )
    
except Exception as e:
    print(f"Collection '{collection_name}' does not exist, creating new collection...")
    
    # Load and process documents
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
    # Split documents
    doc_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    
    splitted_docs = doc_splitter.split_documents(docs)
    print(f"Number of documents after splitting: {len(splitted_docs)}")
    
    # Create new collection and store documents
    qdrant = QdrantVectorStore.from_documents(
        client=client,
        documents=splitted_docs,
        embedding=vector_embedding_model,
        prefer_grpc=False,
        collection_name=collection_name,
    )
    print(f"Created new collection '{collection_name}' and indexed documents")

while True:
    # Test the collection with a query
    query = input("Enter your query: ")

    if query.lower() in ["exit", "quit"]:
        print("Exiting the program.")
        break

    # llm_generate_query = 

    results = qdrant.similarity_search_with_score(query, k=2)

    print("\nSearch Results:")
    for i, (doc, score) in enumerate(results, 1):
        print(f"\nResult {i} (Similarity Score: {score:.4f}):")
        # print(f"Content: {doc.page_content}")
        # print(f"Source: {doc.metadata.get('source', 'Unknown')}")
        # print(f"Page: {doc.metadata.get('page', 'Unknown') + 1}")
        print(f"---------------------------------------------------------", end="\n")