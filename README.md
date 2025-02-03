# Customer Support Management Platform with RAG Chatbot

Welcome to the **Customer Support Management Platform**! This project is designed to streamline customer support by combining a discussion forum with an intelligent chatbot powered by Retrieval Augmented Generation (RAG). Whether your users prefer to post questions and engage in community discussions or interact with a smart chatbot, our platform provides a comprehensive solution tailored for organizational customer support.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture & Flow Diagrams](#architecture--flow-diagrams)
  - [Application Flow](#application-flow)
  - [RAG Operation Flow](#rag-operation-flow)
  - [Hybrid RAG Flow](#hybrid-rag-flow)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Overview

The **Customer Support Management Platform** is built to empower organizations with a robust tool for handling customer queries. It offers:

- **Discussion Forum:** Users can post questions and participate in discussions, similar to a traditional forum. Community-driven answers are encouraged, and when an answer is marked as official, it is automatically added to the chatbot's knowledge base.
- **Intelligent Chatbot:** Integrated with Retrieval Augmented Generation (RAG), the chatbot leverages both simple RAG and Hybrid RAG mechanisms to provide context-aware responses. It uses the Gemini API for high-quality answer generation, while also supporting on-device LLM models as an alternative when compute resources allow.
- **Admin Controls:** Organization admins can manage and add reference documents to improve the chatbot’s response quality by expanding its underlying knowledge base.

This multi-faceted approach ensures that customers receive accurate and timely support through both human and AI-driven responses.

---

## Key Features

- **Discussion Forum**
  - Post questions and answers.
  - Community engagement and collaboration.
  - Official answers can be flagged, enriching the chatbot’s knowledge base.
  
- **Chatbot with RAG**
  - **Simple RAG:** Retrieves relevant documents and generates responses based on them.
  - **Hybrid RAG:** Combines on-device LLM capabilities with external API-powered (Gemini API) responses for optimized performance.
  
- **Knowledge Base Management**
  - Automatic integration of marked official answers.
  - Admins can upload and manage reference documents.
  
- **Admin Interface**
  - Document management for reference updates.
  - Monitoring user interactions and flagged responses.

- **Scalable & Flexible Architecture**
  - Built on **Flask** for the web framework.
  - **SQLite** for lightweight, local database management.
  - **Elasticsearch** for vector database storage enabling efficient similarity search and retrieval.
  
- **Advanced AI Integration**
  - Integration with **Gemini API** for advanced natural language processing.
  - Option for on-device LLM models to balance server compute loads.

---

## Architecture & Flow Diagrams

### Application Flow

The overall application workflow is designed to provide a seamless experience for users and admins alike. Below is an illustrative diagram of the high-level flow:

![orgwork](https://github.com/user-attachments/assets/7955a360-928c-4f57-8921-c85314930200)
![userwoek](https://github.com/user-attachments/assets/06f9a53e-392f-4093-89bc-2a28b3ed088b)
![modwork](https://github.com/user-attachments/assets/c129e681-7b5a-4c1d-9a12-03f7708d7115)
![hybridrag](https://github.com/user-attachments/assets/2d9ee6a2-7df1-4607-8863-027ef3ceaa8c)

**Description:**

1. **User Interaction:** Users post questions in the discussion forum or interact directly with the chatbot.
2. **Data Storage:** All interactions are stored in SQLite, while user queries and documents are indexed in Elasticsearch for quick retrieval.
3. **Response Generation:** 
   - The chatbot queries the knowledge base using RAG techniques.
   - If a question is posed in the forum, community responses are collected.
4. **Knowledge Base Update:** Official answers flagged by moderators/admins are added to the knowledge base, ensuring continuous learning.

---

### RAG Operation Flow

The RAG component is a critical element that fetches and synthesizes data to generate accurate responses. Here’s a simplified flow of how RAG works:

**Description:**

1. **Query Reception:** The user question is received by the chatbot.
2. **Document Retrieval:** 
   - The system uses Elasticsearch to retrieve the most relevant documents based on vector similarity search.
3. **Response Generation:**
   - The retrieved documents are fed into the Gemini API (or an on-device LLM model) for generating the answer.
4. **Response Delivery:** The synthesized response is returned to the user.

---

### Hybrid RAG Flow

For scenarios requiring a balance between external API calls and local computation, the Hybrid RAG flow is utilized:

**Description:**

1. **Initial Query Processing:** User query is processed.
2. **Dual Path Execution:**
   - **External Path:** The query is sent to the Gemini API for a high-quality response.
   - **Local Path:** Simultaneously, an on-device LLM model processes the query.
3. **Result Comparison & Synthesis:** 
   - The results from both paths are compared.
   - The best or most confident answer is selected or a hybrid answer is generated.
4. **Final Response:** The synthesized answer is delivered to the user.

---

## Technology Stack

- **Backend Framework:** [Flask](https://flask.palletsprojects.com/)
- **Database:** [SQLite](https://www.sqlite.org/index.html) for primary storage.
- **Vector Search:** [Elasticsearch](https://www.elastic.co/elasticsearch/) for vector database storage.
- **AI Integration:**
  - [Gemini API](https://www.example.com/gemini-api) for high-quality response generation.
  - On-device LLM models for local processing and fallback.
- **Frontend:** Standard HTML,CSS,JS served by Flask.
- **Additional Tools:** 
  - Docker (optional) for containerized deployments.
  - Python 3.8+ for backend development.

---

## Installation

### Prerequisites

- **Python 3.8+**
- **pip** package manager
- **SQLite** (bundled with Python)
- **Elasticsearch** instance (local or hosted)
- (Optional) **Docker** for containerized deployment

### Clone the Repository

```bash
git clone https://github.com/yourusername/customer-support-platform.git
cd customer-support-platform
```

### Set Up a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file in the project root with the following configurations:

```dotenv
# Flask settings
FLASK_APP=app.py
FLASK_ENV=development

# Elasticsearch settings
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# Gemini API settings
GEMINI_API_KEY=your_gemini_api_key_here
```

### Setting Up Elasticsearch

Make sure your Elasticsearch instance is running. You can start a local instance using Docker:

```bash
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:7.10.1
```

### Initialize the Database

Run the following commands to create and initialize the SQLite database:

```bash
flask db init
flask db migrate
flask db upgrade
```

---

## Usage

### Running the Application

Start the Flask development server:

```bash
flask run
```

By default, the application will be accessible at [http://127.0.0.1:5000](http://127.0.0.1:5000).

### Forum Interaction

- **Posting Questions:** Users can post questions via the discussion forum interface.
- **Answering Questions:** Community members can reply to questions.
- **Marking Official Answers:** Moderators or admins can mark an answer as official, which will automatically update the chatbot’s knowledge base.

### Chatbot Interaction

- **Initiating a Chat:** Access the chatbot interface from the main menu.
- **RAG-based Responses:** The chatbot retrieves context from the knowledge base and reference documents to generate a response.
- **Hybrid RAG:** Depending on server load and configuration, the chatbot may use either the Gemini API or an on-device LLM model.

### Admin Dashboard

Admins can:
- Upload and manage documents for the chatbot’s reference.
- Monitor forum activities and user interactions.
- Configure system settings (e.g., switching between RAG modes).

---
