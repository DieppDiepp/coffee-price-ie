# Coffee Price IE

This project collects and processes coffee price information from online news sources.

## VOV Crawling Pipeline

This module implements a crawling and extraction workflow for coffee price articles from VOV.

### Pipeline Overview

The pipeline consists of three steps:

1. Crawl article links
2. Crawl raw article content
3. Extract structured coffee price data using LLM

```
VOV Website
   ↓
Crawl links
   ↓
Crawl article content
   ↓
LLM extraction
   ↓
Structured coffee price dataset
```

---

## Notebooks

### 1. vov_1_crawl_links.ipynb
Collect article links related to coffee prices from VOV.

### 2. vov_2_crarwl_data_from_links.ipynb
Crawl raw article content from the collected links.

### 3. vov_3_extract_data.ipynb
Use an LLM to extract structured coffee price information from the raw article text.

---

## Generated Data

### vov_coffee_1_links.csv
Contains all collected article links.

### vov_coffee_2_articles.csv
Contains raw article content.

### vov_coffee_3_prices.csv
Contains structured coffee price data extracted from articles.

---

## Data Pipeline

The workflow transforms unstructured news articles into a structured dataset of coffee prices.

```
News Articles
     ↓
Web Crawling
     ↓
Raw Article Dataset
     ↓
LLM Extraction
     ↓
Structured Coffee Price Dataset
```