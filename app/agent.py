import os
import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

from app.vector_store import qdrant_client, COLLECTION_NAME, get_qdrant_filter_for_role

load_dotenv()
logger = logging.getLogger(__name__)


def get_agent_pipeline(meeting_id: str, role: str):
    """
    Builds the LangChain RAG pipeline scoped to a specific meeting and role.

    - admin: retriever searches ALL vectors for the meeting
    - member: retriever is filtered to only 'public' visibility vectors

    This ensures a member asking "catch me up" can NEVER receive
    admin-only content in their AI-generated summary.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("No GOOGLE_API_KEY found! The Agent will not be able to answer questions.")
        return None

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    # Role-scoped filter: members cannot retrieve admin-only chunks
    qdrant_filter = get_qdrant_filter_for_role(meeting_id, role)

    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 6,
            "filter": qdrant_filter
        }
    )

    system_prompt = (
        "You are 'Catch-Me-Up', an AI Meeting Copilot that helps people understand what they missed.\n"
        "Your job is to summarize specific time windows or answer questions like 'what happened in the last 10 minutes?'\n"
        "The context below contains timestamped, chronological meeting transcripts.\n"
        "Use the timestamps to anchor your answer to the correct window of time.\n"
        "Keep your response concise, structured as bullet points, and professional.\n"
        "Never expose or hint at the existence of content the user does not have access to.\n"
        "\n"
        "Relevant transcript context:\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    return rag_chain


async def ask_copilot(meeting_id: str, question: str, role: str = "member") -> str:
    """
    Executes the visibility-scoped LangChain RAG pipeline.
    Role determines which Qdrant vectors are searched.
    """
    chain = get_agent_pipeline(meeting_id, role)
    if not chain:
        return "Error: Copilot is offline. Please set your GOOGLE_API_KEY in the .env file!"

    try:
        response = await chain.ainvoke({"input": question})
        return response["answer"]
    except Exception as e:
        logger.error(f"Failed to query Gemini Agent: {e}")
        return "Sorry, I ran into an issue while processing your question."
