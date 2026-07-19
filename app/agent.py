import os
import logging
from dotenv import load_dotenv

# Import LangChain and Google GenAI specific tools (Just like in Krish Naik's Course!)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

from app.vector_store import qdrant_client, COLLECTION_NAME

# Load the environment variables (like GEMINI_API_KEY) from the .env file
load_dotenv()

logger = logging.getLogger(__name__)

def get_agent_pipeline():
    """
    Builds the LangChain RAG pipeline.
    This connects the Qdrant Vector Store to the Gemini LLM so it can answer questions based on the meeting context!
    """
    
    # 1. Check if the user has provided their Gemini API key
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("No GOOGLE_API_KEY found! The Agent will not be able to answer questions.")
        return None
        
    # 2. Initialize the Gemini LLM
    # We use gemini-1.5-flash because it is incredibly fast and cheap, perfect for real-time agents.
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    
    # 3. Setup Embeddings
    # We switch to local HuggingFace embeddings to prevent API 404 errors!
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # 4. Connect to our existing Qdrant Vector Store (from Chunk 4)
    # This turns our database into a LangChain "Retriever"
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    
    system_prompt = (
        "You are 'Catch-Me-Up', an advanced AI Meeting Copilot.\n"
        "Your primary job is to generate Minutes of the Meeting (MOM) or summarize specific missed durations.\n"
        "The context provided below contains chronological transcripts with exact timestamps.\n"
        "If the user asks what happened in the 'last 5 minutes' or a specific time window, "
        "use the timestamps to filter the context logically before summarizing.\n"
        "Keep your answer concise, professional, and structured as bullet points if summarizing.\n"
        "\n"
        "Chronological Context from the meeting:\n"
        "{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    return rag_chain

async def ask_copilot(meeting_id: str, question: str) -> str:
    """
    Executes the LangChain RAG pipeline to answer a user's question.
    """
    chain = get_agent_pipeline()
    if not chain:
        return "Error: Copilot is offline. Please set your GOOGLE_API_KEY in the .env file!"
        
    try:
        response = await chain.ainvoke({"input": question})
        return response["answer"]
    except Exception as e:
        logger.error(f"Failed to query Gemini Agent: {e}")
        return "Sorry, I ran into an issue while processing your question."
