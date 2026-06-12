#!/bin/bash
# Finder — Full Pipeline Script
# Usage: bash scripts/run_pipeline.sh

set -e

echo "🔍 Finder Search Engine — Full Pipeline"
echo "========================================="
echo ""

# Step 1: Crawl
echo "Step 1/4: Crawling web pages..."
python -m finder crawl --seeds scripts/seed_urls.txt --depth 2 --workers 5
echo ""

# Step 2: PageRank
echo "Step 2/4: Computing PageRank scores..."
python -m finder rank
echo ""

# Step 3: Index
echo "Step 3/4: Indexing into Elasticsearch..."
python -m finder index
echo ""

# Step 4: Serve
echo "Step 4/4: Starting search server..."
echo "Open http://localhost:8000 in your browser"
python -m finder serve
