<div align="center">

<h1>Shubankar's Mini AI RAG Assistant</h1>


<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white">
  <img alt="Chroma" src="https://img.shields.io/badge/Chroma-0.5-FF6B6B">
  <img alt="Redis" src="https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white">
</p>

</div>

---

## Hello, judges!!!

My name is **Shubankar**. Thank you for opening this README. This project is a small but complete **Retrieval-Augmented Generation (RAG)** system that answers questions about your own PDFs - with citations, hybrid retrieval, multi-provider LLM support, and a fully Dockerized deployment.

It is built to be **accurate**: answers are grounded in the documents users upload. If the context does not contain the answer, the assistant says so.

If you have five minutes, skim the sections below in order. If you have thirty seconds, jump straight to [Key Architectural Decisions](#key-architectural-decisions) and [Why this is production-ready](#why-this-is-production-ready).

---

## Contents

1. [Chosen Theme](#chosen-theme)
2. [Functional Requirements Satisfied](#functional-requirements-satisfied)
3. [Features Added for Better User Experience](#features-added-for-better-user-experience)
4. [Key Architectural Decisions](#key-architectural-decisions)
5. [Important Modules](#important-modules)
6. [Data Flow, in Plain Language](#data-flow-in-plain-language)
7. [Why This Is Production-Ready](#why-this-is-production-ready)
8. [How to Run](#how-to-run)

---

## Chosen Theme

**Option 1 - Build a Mini AI Knowledge Assistant (RAG).**

A user uploads one or more PDFs. The system extracts, chunks, embeds, and stores them. When the user asks a question, the system retrieves the most relevant chunks using a **hybrid of keyword and semantic search**, sends them to a large language model as context, and streams back an answer with **source citations**.

The design goal was not "make it work" - it was "make it work well, with the right foundations, in a way that a real product could ship."

---

## Functional Requirements Satisfied

Every requirement from the problem statement is implemented, and where a design choice was available, the more thorough option was chosen.

| # | Requirement | How it is satisfied |
|---|---|---|
| 1 | Use a PDF or collection of documents as the knowledge source | PDF upload endpoint accepts multiple documents; each is parsed, chunked, and stored with source metadata |
| 2 | Extract and process document content | A deterministic Java-based parser (OpenDataLoader PDF) extracts text, headings, tables, and images as structured Markdown and JSON |
| 3 | Split content into appropriate chunks | Heading-aware chunker preserves document structure; chunk boundaries follow sections rather than arbitrary character counts |
| 4 | Generate embeddings | Local embeddings via Ollama's `nomic-embed-text` (768-dim), with an OpenAI fallback available through configuration |
| 5 | Store and retrieve using a vector store | Chroma DB in HTTP client/server mode; vectors persisted, cosine similarity for retrieval |
| 6 | Accept questions from the user | SSE streaming chat endpoint; credentials passed per request, nothing persisted server-side |
| 7 | Retrieve relevant info and generate answers using an LLM | Hybrid retrieval (BM25 + semantic + RRF) assembles a context block; the universal LLM client streams the answer |
| 8 | Answers primarily based on the knowledge source | System prompt explicitly forbids answering outside the provided context; source citations surface which chunks were used |
| 9 | Simple and usable interface | Next.js frontend with a focused chat UI, provider selector, upload panel, and export buttons |

---

## Features Added for Better User Experience

These go beyond the base requirements. Each was chosen because it solves a real problem a user would hit.

### 1. Bring Your Own Model - Cloud or Local

The frontend lets the user pick a provider from a dropdown:

- **Cloud**: OpenAI, Anthropic Claude, Google Gemini, DeepSeek
- **Local**: Ollama (any model), or a local GGUF model served by `llama.cpp`

Every provider is accessed through the **same OpenAI-compatible interface**. The user enters only an API key for cloud providers, or a server URL for local ones. The key never leaves the browser tab unless a request is being made - nothing is stored on the server.

### 2. Connection Test Before Chat

Before a user commits to a provider, they click **"Test connection"**. The backend sends a minimal request to the provider and returns either **"Connected"** or **"Failed to connect, wrong API"**. This turns a slow debugging session into a one-click check.

### 3. Source Citations

Every answer includes a numbered list of the chunks that grounded it - file name and section heading. The user can verify the model's answer against the original document, which is essential for trust.

### 4. Conversation History

Multi-turn conversations are persisted in Redis with a rolling window, semantic recall of older messages, and auto-summarization when the history grows. The user can pick up where they left off without the LLM losing track of earlier questions.

### 5. Export Chat as Markdown, JSON, or PDF

Any conversation can be exported in three formats. Markdown for sharing in a repo, JSON for programmatic use, PDF for a printed record. A separate "export summary" button generates an LLM-written summary of the conversation as Markdown or PDF.

### 6. Structured PDF Parsing

The parser preserves reading order, tables, images, and heading hierarchy. It produces Markdown that the LLM can reason over directly. This is a deliberate departure from naive PDF extraction, which flattens structure and loses important context.

### 7. Local Embeddings, Zero Setup for the User

The system ships with `nomic-embed-text` pulled automatically inside the Docker stack. The user does not install Ollama or configure anything. Their only input is the chat model key.

### 8. Hybrid Retrieval

Combining BM25 (keyword) with semantic search via **Reciprocal Rank Fusion** gives meaningfully higher recall than either method alone, especially for queries involving specific terms, numbers, or proper nouns.

### 9. Streaming Responses

Answers appear token by token via Server-Sent Events. The user sees progress immediately, even for long answers from slow local models.

---

## Key Architectural Decisions

The choices below shape the entire system. Each is explained in plain language, with the trade-off made explicit.

### Next.js for the frontend, not plain React

Plain React renders entirely in the browser. Search engines see an empty HTML shell. Next.js pre-renders pages on the server, so the landing page and provider documentation are fully indexable. For a public website, this is the difference between being found and not being found.

### Nginx for serving the frontend, not `next start`

The Next.js app is exported as a **static site**. Nginx serves the resulting HTML, CSS, and JS from disk. This means:

- The image is ~50 MB instead of ~200 MB.
- It uses ~5 MB of RAM instead of ~150 MB.
- It handles thousands of concurrent requests without breaking a sweat.
- No Node.js runtime runs in production.

If the app later needs server-rendered pages with per-request data, this decision is reversible. For the current scope, Nginx is the right tool.

### Chroma as the vector database

Chroma is the SQLite of vector databases - easy to run, no cluster to manage, and it persists to disk. It supports the HTTP client/server mode that allows the backend to talk to it as a separate service. This is a deliberate choice over heavier options like Milvus or Qdrant, which would be overkill for this project's scale.

### OpenDataLoader PDF for parsing, not PyPDF

`PyPDF` and similar pure-Python parsers flatten documents. They lose heading structure, mangle tables, and produce text in the wrong reading order for multi-column layouts. **OpenDataLoader PDF** is a Java-based tool that:

- Preserves the heading hierarchy of the original document.
- Detects and reconstructs tables.
- Extracts images with bounding boxes.
- Produces Markdown that LLMs consume well.

The trade-off is that it requires a Java runtime in the backend image (which the Dockerfile installs). That is a small price for structured parsing.

### Hybrid retrieval: BM25 + semantic + RRF

Pure semantic search (vector similarity) misses exact matches for SKUs, error codes, and rare proper nouns. Pure keyword search (BM25) misses paraphrases and synonyms. **Reciprocal Rank Fusion** merges both rankings without needing to compare incompatible scores. The result is higher recall at every `k`, and it is the difference between an answer that cites the right chunk and one that cites something adjacent.

### Multiple AI providers via one universal client

Every major provider now exposes an OpenAI-compatible `/v1/chat/completions` endpoint. Rather than writing a client per provider, the backend uses a **single client** and swaps the base URL and API key. Local Ollama and GGUF servers also speak this protocol. One client, six providers, no branching.

This also solves the **browser CORS problem** for local LLMs. A web page cannot call `http://localhost:11434` directly. The backend proxies the request, so the browser only ever talks to the backend.

### Redis for caching and session storage

Redis holds conversation history as lists with TTL, and caches embeddings and completions in a two-tier scheme (in-memory LRU in front of a shared Redis cache). A third, semantic cache tier is defined and ready to be enabled. This is what makes multi-turn conversations cheap and fast.

### FastAPI for the backend

FastAPI is async-first, which matters because the backend spends most of its time waiting on network calls to Ollama, OpenAI, Redis, and Chroma. It has first-class SSE support through `sse-starlette`, automatic OpenAPI docs at `/docs`, and Pydantic for request and response validation. A Django or Flask stack would either be synchronous or need extra plumbing for the same capabilities.

### Docker Compose for orchestration

Five services - Ollama, Chroma, Redis, backend, frontend - with healthchecks and dependency ordering. One command (`docker compose up`) brings the entire stack online. The user's only requirement is Docker.

---

## Important Modules

The system is organized into clear layers. Each module has one job.

### Backend

| Module | Responsibility |
|---|---|
| `app/main.py` | FastAPI application, CORS, correlation IDs, startup and shutdown hooks |
| `app/config.py` | Central settings loaded from environment variables |
| `app/logging_config.py` | Structured JSON logging with correlation IDs |
| `app/core/pdf_parser.py` | Deterministic PDF parsing into Markdown and structured JSON |
| `app/core/chunker.py` | Heading-aware chunking that preserves document structure |
| `app/core/embeddings.py` | Local or cloud embeddings through a single interface |
| `app/core/vector_store.py` | Chroma HTTP client wrapper |
| `app/core/bm25_index.py` | BM25 index built from stored chunks, persisted to disk |
| `app/core/retriever.py` | Hybrid retrieval and Reciprocal Rank Fusion |
| `app/core/llm_client.py` | Universal OpenAI-format client for all six providers |
| `app/core/cache.py` | Two-tier cache (in-memory LRU + Redis) with semantic tier hook |
| `app/core/session_store.py` | Redis-backed conversation history |
| `app/services/ingestion.py` | Upload → parse → chunk → embed → store pipeline |
| `app/services/chat_service.py` | Context assembly, retrieval, prompt construction, SSE streaming |
| `app/services/context_manager.py` | Hot window, semantic recall, auto-summarization |
| `app/services/export_service.py` | Chat export as Markdown, JSON, PDF; summary generation |
| `app/api/routes/` | HTTP and SSE endpoints, grouped by concern |

### Frontend

| Module | Responsibility |
|---|---|
| `src/app/layout.tsx` | Root layout, SEO metadata, site navigation |
| `src/app/page.tsx` | Landing page, server-rendered for SEO |
| `src/app/providers/page.tsx` | Provider documentation, server-rendered |
| `src/app/chat/page.tsx` | Chat page: connection, upload, chat composition |
| `src/components/ConnectionForm.tsx` | Provider and credential selection with connection test |
| `src/components/ChatWindow.tsx` | SSE-driven chat interface |
| `src/components/MessageBubble.tsx` | Single message rendering |
| `src/components/SourceList.tsx` | Citation display |
| `src/components/UploadPanel.tsx` | PDF upload and ingestion feedback |
| `src/components/ExportButtons.tsx` | Chat export triggers |
| `src/lib/api.ts` | HTTP helpers for the backend |
| `src/lib/types.ts` | Shared TypeScript types |

---

## 🔄 Data Flow, in Plain Language

There are two flows: **ingestion** (once per document) and **query** (once per question).

### Ingestion - when a user uploads a PDF

1. The PDF lands in `backend/data/uploads/`.
2. The parser reads it and produces two outputs: a Markdown file for the LLM, and a structured JSON file with element positions.
3. The chunker splits the Markdown by heading, producing sections with metadata (source file, heading, level).
4. Each chunk is embedded with `nomic-embed-text`, producing a 768-dim vector.
5. Chroma stores the vector, the chunk text, and the metadata.
6. A BM25 index is rebuilt from all stored chunks and saved to disk.

### Query - when a user asks a question

1. The user's message is saved to Redis (session history).
2. The system retrieves the last `HOT_WINDOW_SIZE` messages, plus any older messages that are semantically similar to the question, plus a rolling summary if the history is long.
3. The question is embedded and sent to Chroma (semantic search) and to BM25 (keyword search) in parallel.
4. The two ranked lists are merged by Reciprocal Rank Fusion. The top `k` chunks are the ones the LLM will see.
5. The chunks are formatted into a numbered context block. The system prompt instructs the LLM to answer using only this context.
6. The request is sent to the user's chosen provider (cloud or local) through the universal client.
7. Tokens stream back through Server-Sent Events to the browser.
8. When the stream ends, the assistant's full message is saved to Redis.

### Export - when a user wants a copy

The conversation is read from Redis, formatted by `export_service.py`, and returned as a downloadable file in the requested format.

---

## Why This Is Production-Ready

"Production-ready" is often used loosely. Here is what it means in this project.

### Dockerized, five services, one command

The user runs `docker compose up` and the entire stack - Ollama, Chroma, Redis, backend, frontend - comes online in the correct order. Healthchecks gate startup so nothing races. Data persists in named volumes and on the host's `backend/data/` directory.

### Two deployment paths, no fragmentation

The same code runs in two modes:

- **Docker**: everything in containers.
- **Local development**: `make dev` starts all three services natively for fast iteration.

Both paths are validated. Neither is a second-class citizen.

### No API keys baked into images

Secrets live in `.env`, which is excluded by `.gitignore` and `.dockerignore`. The image never contains them. Users bring their own keys at runtime.

### Local-first, cloud-optional

Embeddings run locally. The chat model can be local or cloud. A user with no API keys can run the full pipeline with Ollama alone. A user with a cloud key gets faster, larger models. Neither is forced.

### Structured logging with correlation IDs

Every log line is JSON, with a timestamp, level, logger name, message, and correlation ID. Tracing a request across the backend, the retriever, the LLM client, and the response is a grep away. This is what makes debugging in production tractable.

### Graceful degradation

If Redis is down, the app still works - single-turn Q&A functions without conversation history. If Chroma is unreachable, health checks report it and uploads fail with a clear message. The system fails visibly and correctly, not silently.

### Caching at two levels, ready for three

The in-memory LRU catches repeated requests within a process. Redis catches them across processes. A semantic cache tier is defined and can be enabled with a config flag.

### Versioned, health-checked, restartable

Every service has a healthcheck. Every image is pinned (except `ollama/ollama:latest`, which will be pinned once a stable version is confirmed). Every container has `restart: unless-stopped`. A crashed service recovers without manual intervention.

### Small images, fast startup

The frontend image is roughly 50 MB (Nginx + static files). The backend image is roughly 300 MB (Python + Java + dependencies). Startup is seconds, not minutes.

### Testable boundaries

Each module has a single responsibility. `retriever.py` can be tested without spinning up Chroma - it takes a vector store and BM25 index as dependencies. `chunker.py` is pure. `pdf_parser.py` takes a file path and returns a dataclass. Unit tests are straightforward to write, and the layout anticipates them.

### Honest error messages

"Failed to connect, wrong API" beats a stack trace. "Cannot find it in the uploaded documents" beats a hallucinated answer. The system's defaults are set so that failure is legible.

---

## How to Run

### With Docker (recommended)

```bash
git clone https://github.com/Shubankar-Sridhar/Shubankar-s-Mini-AI-RAG-Assistant.git
cd Shubankar-s-Mini-AI-RAG-Assistant
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d --build
```

Then open http://localhost:3000, pick a provider, and paste your API key (or use Ollama with no key).

First run takes 5-10 minutes while Docker pulls images and downloads the embedding model. Subsequent runs take seconds.


Without Docker (local development)
```bash
git clone https://github.com/Shubankar-Sridhar/Shubankar-s-Mini-AI-RAG-Assistant.git
cd Shubankar-s-Mini-AI-RAG-Assistant
make setup        
make dev-chroma   
make dev          
```
Requires Python 3.11, Node.js 20, Java 11+, and a Redis instance. See the Makefile's help target for all commands.

Stopping
```bash
# Docker
docker compose -f docker/docker-compose.yml down

# Local
make stop
```

Thank you for taking the time to read through this!!!
