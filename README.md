# Application Overview

This application integrates OpenAI embeddings, ChromaDB, and OpenAI Chat to provide advanced search and conversational capabilities. It leverages the power of OpenAI's language models and ChromaDB's efficient data storage and retrieval to deliver a seamless user experience.

## Features

1. **Search in ChromaDB by Proximity**:
   - Perform searches in ChromaDB using proximity-based queries. This feature allows users to find data points that are closest to a given embedding, enabling efficient and relevant search results.

2. **OpenAI Chat Integration**:
   - Engage in interactive conversations using OpenAI's chat models. The application supports dynamic context generation and response handling to facilitate meaningful interactions.

3. **Embedding Generation**:
   - Generate embeddings for text inputs using OpenAI's embedding models. These embeddings are used for both search and chat functionalities, ensuring consistent and accurate data representation.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Access to OpenAI API

### Applications/points of interaction

1. Web API - default 127.0.0.1:800
   1. search - Basic REST endpoint
   2. chat - SSE endpoint to interact with OpenAI chat
2. Telnet Console - default 127.0.0.1:8023
   1. used to ingest data in ChromaDB
      1. run ingest
      2. cancel
      3. exit
      4. shutdown

### Implementation details/decisions

1. For ChromaDB we added a connection pool to limit the access concurrency and reuse connections.
2. Ingestion script was added to the application because ChromaDB was marked as thread safe but not process safe
3. Right now, because of the limitation of my free OpenAI account the embeddings are randomly generated for me to be able to test
4. Created a pattern of singleton and static classes (methods) for things tha are common
   1. Logger for logging but with modules in mind
   2. Config to load all different kind of configuration and not read from env all the time
   3. Connectors for ChromaDB and OpenAI
5. Added a safe close mechanism for the entire application, releasing the resources (it might need some work though)
6. I over complicated the implementation because I wanted to learn a bit about the limitations of python and what I can work with
7. Points that I did not cover : canceling of the SSE from openai chat in case the original client disconnected. Found something on the web but I need to learn more about it because what I found was a bit complicated and I did not want to spend to much time on it.
8. I still have some reading to do about the asyncio library and what are the capabilities that I can work with
9. Wanted to also add a way to reset the Chromadb for testing purposes but did not get to it
