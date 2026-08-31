# Docker

```bash
cp ../.env.example ../.env      # then add at least one LLM API key
docker compose up --build
```

- API: http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard

The first start downloads the embedding and reranker weights (~150 MB) into the
`hf-cache` volume; subsequent starts reuse it.
