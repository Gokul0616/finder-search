# 🔍 Finder — Search Engine from Scratch

A fully functional search engine built from scratch in Python + Next.js. Crawl the web, build a link graph, compute PageRank, index with Elasticsearch, and search with a Google-style UI.

## Architecture

```
Crawler → MongoDB → PageRank → Elasticsearch → FastAPI → Next.js
```

| Component | Tech |
|-----------|------|
| **Crawler** | Python, httpx (async HTTP/2), BeautifulSoup, lxml |
| **Database** | MongoDB Atlas |
| **PageRank** | NetworkX directed graph |
| **Indexing** | Elasticsearch (BM25) |
| **Text Extraction** | Trafilatura |
| **API** | FastAPI + Redis caching |
| **Frontend** | Next.js + TypeScript + Axios |

## Project Structure

```
Finder/
├── finder/                 # Python backend
│   ├── crawler/            # Web crawler (frontier, fetcher, parser, storage)
│   ├── graph/              # Link graph builder + PageRank
│   ├── indexer/            # Elasticsearch indexer + text extraction
│   ├── ranker/             # BM25 + PageRank combined scorer
│   ├── api/                # FastAPI query server
│   ├── db/                 # MongoDB layer (motor async driver)
│   └── cli.py              # CLI commands
├── frontend/               # Next.js search UI
│   └── src/
│       ├── app/            # Pages (landing, search results)
│       ├── components/     # SearchBar, ResultCard, Pagination, Header
│       ├── lib/            # Axios client with interceptors, API services
│       └── types/          # TypeScript types
├── scripts/                # Seed URLs, pipeline script
└── requirements.txt        # Python dependencies
```

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Elasticsearch 8.x (running locally on port 9200)
- Redis (running locally on port 6379)

### Backend Setup

```bash
# Create virtual environment & install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the crawler
python -m finder crawl --seeds scripts/seed_urls.txt --depth 2

# Compute PageRank
python -m finder rank

# Index into Elasticsearch
python -m finder index

# Start the API server
python -m finder serve
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 to search.

## CLI Commands

```bash
python -m finder crawl     # Crawl web pages from seed URLs
python -m finder rank      # Compute PageRank scores
python -m finder index     # Index pages into Elasticsearch
python -m finder serve     # Start FastAPI server (port 8000)
python -m finder pipeline  # Run all steps end-to-end
python -m finder stats     # Show crawl statistics
```

## How Ranking Works

```
final_score = α × BM25_score + β × PageRank_score
```

- **BM25**: Text relevance from Elasticsearch (default scoring)
- **PageRank**: Link authority computed from the crawled web graph
- **Title boost**: +20% if query appears in title
- **Exact phrase boost**: +15% if exact query found in content
- **α = 0.7, β = 0.3** (configurable)

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/search?q=...&page=1&size=10` | Search pages |
| `GET /api/stats` | System statistics |
| `GET /docs` | Swagger API docs |

## License

MIT
