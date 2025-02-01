import os
from .. import es, embedding_model
from langchain_community.llms.ollama import Ollama
from langchain_core.prompts import ChatPromptTemplate

index_name = os.getenv("QA_INDEX_NAME")

# Index question-answer pairs for a specific organisation_id
def index_qa_pairs(qa_pair, organisation_id, question_id):
    question = qa_pair["question"]
    answer = qa_pair["answer"]
    embedding = embedding_model.encode(question).tolist()  # Embed the question
    
    # Index the document
    es.index(index=index_name, document={
        "organisation_id": organisation_id,
        "question_id": question_id,
        "question": question,
        "answer": answer,
        "embedding": embedding
    })
    print(f"Indexed {len(qa_pair)} question-answer pairs for organisation_id {organisation_id}.")

# Search for the most relevant answer based on a query
def search_answer(query, organisation_id, top_k=3):
    query_embedding = embedding_model.encode(query).tolist()
    
    # Construct the search query
    search_query = {
        "query": {
            "bool": {
                "filter": [{"term": {"organisation_id": organisation_id}}]
            }
        },
        "knn": {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": top_k,
            "num_candidates": 50
        }
    }

    # Perform the search
    response = es.search(index=index_name, body=search_query, size=top_k, _source_includes=["question", "answer"])

    # Extract and display the results
    results = []
    for hit in response["hits"]["hits"]:
        results.append({
            "question": hit["_source"]["question"],  # Explicitly extract question
            "answer": hit["_source"]["answer"],      # Explicitly extract answer
            "score": hit["_score"]
        })

    return results