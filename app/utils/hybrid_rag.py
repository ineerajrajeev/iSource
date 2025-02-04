import os
from .. import es, embedding_model
import PyPDF2
from langchain_community.llms.ollama import Ollama
from langchain_core.prompts import ChatPromptTemplate

index_name = os.getenv("DOC_INDEX_NAME")

def index_documents(documents, organisation_id):
    for doc in documents:
        try:
            embedding = embedding_model.encode(doc["text"]).tolist()
            es.index(index=index_name, id=doc["id"], document={
                "organisation_id": organisation_id,
                "text": doc["text"],
                "embedding": embedding
            })
            print(f"Document ID {doc['id']} indexed with organisation_id {organisation_id}.")
        except Exception as e:
            print(f"Failed to index document ID {doc['id']}: {e}")


def normalize_scores(scores):
    if not scores:
        return {}
    min_score = min(scores.values())
    max_score = max(scores.values())
    return {doc_id: (score - min_score) / (max_score - min_score) for doc_id, score in scores.items()}


def reciprocal_rank_fusion(bm25_results, semantic_results, k=60):
    bm25_results = normalize_scores(bm25_results)
    semantic_results = normalize_scores(semantic_results)

    fused_scores = {}
    for doc_id, score in bm25_results.items():
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (score + k)
    for doc_id, score in semantic_results.items():
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (score + k)
    return fused_scores


def get_next_elasticsearch_id(index_name):
    if not es.indices.exists(index=index_name):
        print(f"Index '{index_name}' does not exist. Starting from ID 1.")
        return 1

    query = {
        "size": 0,
        "aggs": {
            "max_id": {
                "max": {
                    "field": "id"
                }
            }
        }
    }
    try:
        response = es.search(index=index_name, body=query)
        max_id = response["aggregations"]["max_id"].get("value", 0)
        return int(max_id) + 1 if max_id else 1
    except Exception as e:
        print(f"Error retrieving max ID: {e}")
        return 1


def pdf_to_documents(pdf_path, organisation_id):
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            print(f"PDF Loaded: {pdf_path} | Total Pages: {total_pages}")

            next_id = get_next_elasticsearch_id(index_name)
            documents = []

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():  # Skip empty pages
                    document = {
                        "id": next_id,
                        "text": text
                    }
                    documents.append(document)
                    print(f"Prepared Document ID {next_id} for indexing.")
                    next_id += 1

            index_documents(documents, organisation_id)
    except Exception as e:
        print(f"Error processing PDF: {e}")


def hybrid_search(query, organisation_id, top_k=3, score_threshold=0):
    # Check if the index exists
    if not es.indices.exists(index=index_name):
        print(f"Index '{index_name}' does not exist.")
        return ""
    else:
        print(f"Index '{index_name}' found.")

    # BM25 Search
    bm25_query = {
        "query": {
            "bool": {
                "must": [{"match": {"text": query}}],
                "filter": [{"term": {"organisation_id": organisation_id}}]
            }
        }
    }
    try:
        bm25_response = es.search(index=index_name, body=bm25_query, size=top_k)
        bm25_results = {
            hit["_id"]: hit["_score"] for hit in bm25_response["hits"]["hits"]
        }
    except Exception as e:
        print(f"BM25 search failed: {e}")
        bm25_results = {}

    # Semantic Search
    query_embedding = embedding_model.encode(query).tolist()
    semantic_query = {
        "query": {
            "script_score": {
                "query": {
                    "bool": {
                        "filter": [{"term": {"organisation_id": organisation_id}}]
                    }
                },
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                    "params": {"query_vector": query_embedding}
                }
            }
        }
    }

    try:
        semantic_response = es.search(index=index_name, body=semantic_query, size=top_k)
        semantic_results = {
            hit["_id"]: hit["_score"] for hit in semantic_response["hits"]["hits"]
        }
    except Exception as e:
        print(f"Semantic search failed: {e}")
        semantic_results = {}

    # Fuse Scores (assuming reciprocal_rank_fusion returns a dict mapping doc_id to a fused score)
    fused_scores = reciprocal_rank_fusion(bm25_results, semantic_results)
    sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    print("Fused Scores:", fused_scores)
    print("Sorted Results:", sorted_results)

    # print("sorted_results", sorted_results)

    # # Collect doc IDs that meet the score threshold
    valid_doc_ids = [doc_id for doc_id, score in sorted_results]
    # if not valid_doc_ids:
    #     print("No documents passed the score threshold.")
    #     return ""

    # Retrieve documents in bulk using mget.
    # (If your mapping disables _source, replace _source_includes with stored_fields and adjust accordingly.)
    try:
        docs_response = es.mget(
            index=index_name,
            body={"ids": valid_doc_ids},
            _source_includes=["text"]
        )
    except Exception as e:
        print(f"Error fetching documents: {e}")
        return ""

    # Extract the "text" field from each returned document.
    result_texts = []
    for doc in docs_response.get("docs", []):
        # Make sure _source exists and contains "text"
        source = doc.get("_source", {})
        text = source.get("text")
        if text:
            result_texts.append(text)

    final_results = " ".join(result_texts) if result_texts else ""
    print(f"Final Results: {final_results}")
    return final_results
