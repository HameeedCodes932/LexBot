# Limitations & Future Work

## Current Limitations

### Performance & Scalability

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| **Synchronous LLM calls** | Each response blocks the request until the LLM finishes; no streaming. | Implement SSE streaming for chat and summarization endpoints. |
| **Single-process embedding** | All `all-MiniLM-L6-v2` embeddings run in-process, which blocks the event loop during generation. | Offload embeddings to a separate worker pool or a dedicated embedding service. |
| **pgvector index tuning** | Default IVFFlat index; recall degrades at scale (>1M chunks). | Switch to HNSW index, tune `lists` and `probes` parameters based on corpus size. |
| **No caching** | Every identical query re-embeds and re-searches the full vector space. | Add Redis caching for query embeddings and common question answers (TTL-based). |
| **Single Redis instance** | Rate limiting state is lost if Redis goes down. | Add Redis Sentinel or move to Redis Cluster for HA. |

### Functional Gaps

| Gap | Reason | Priority |
|-----|--------|----------|
| **No document versioning** | Uploads overwrite previous documents; no history tracked. | High |
| **No batch upload** | Users must upload one file at a time. | Medium |
| **No OCR** | Scanned PDFs (images) cannot be processed. | High for legal use |
| **No collaborative editing** | Multiple users cannot annotate the same document simultaneously. | Medium |
| **No export (PDF/Word)** | Chat responses and analysis cannot be exported. | High |
| **No email notifications** | Obligation deadlines, share invites, etc. have no push notification. | Medium |
| **No document templates** | Users cannot create reusable template contracts from scratch. | Low |
| **Sign-in with Google/GitHub** | Only email+password and SAML SSO are supported. | Medium |
| **Mobile PWA** | App is desktop-responsive but not a true PWA with offline support. | Low |

### Security & Compliance

| Gap | Status | Action |
|-----|--------|--------|
| **Penetration testing** | Not performed | Engage a third-party for annual pentest |
| **Data retention enforcement** | Model field exists but no background job prunes old documents | Add a Celery beat task to enforce `data_retention_days` |
| **Encryption at rest** | Relies on PostgreSQL TDE / disk-level encryption | Document the assumption; add app-level AES-256 for PII fields |
| **SOC 2 Type II audit** | Readiness doc exists, no audit performed | Schedule with a certified CPA firm |

---

## Future Work Roadmap

### Phase 1 — Near-Term (1-2 Months)

- [ ] **Streaming responses** — SSE for chat and summarization (biggest UX improvement)
- [ ] **Document versioning** — Keep history of uploads with diff view
- [ ] **OCR integration** — Use Tesseract or Azure Document Intelligence for scanned PDFs
- [ ] **Export feature** — Download chat results and analysis as PDF/Word
- [ ] **Email notifications** — SendGrid integration for obligation deadlines and share invites
- [ ] **Caching layer** — Redis-based query and embedding cache

### Phase 2 — Medium-Term (3-6 Months)

- [ ] **Fine-tuned legal embedding model** — Custom sentence-transformer trained on legal corpora (CaseLaw, contracts)
- [ ] **Multi-language support** — Detect and translate non-English documents before processing
- [ ] **Advanced clause negotiation** — Suggest alternative language for risky clauses (e.g., "Replace unlimited liability with a cap of X")
- [ ] **Visual analytics dashboard** — Trend analysis of obligation compliance, clause frequency, document risk scores
- [ ] **Celery task queue** — Background processing for large document uploads and batch operations
- [ ] **WebSocket real-time sync** — Collaborative annotations and live typing indicators

### Phase 3 — Long-Term (6-12 Months)

- [ ] **On-premise deployment** — Helm chart for Kubernetes, air-gapped installation
- [ ] **Custom model fine-tuning** — LoRA adapters per organization using their historical data
- [ ] **Document generation** — Generate contract drafts from clause library selections
- [ ] **Advanced eDiscovery** — Keyword + concept search across entire corpus with date filters and custodian tracking
- [ ] **Billing analytics** — Usage forecasting, cost-per-query breakdown, anomaly detection
- [ ] **API Marketplace** — Public developer portal with API key self-service and usage metrics
- [ ] **Regulatory compliance module** — Auto-detect GDPR/CCPA/SOX-relevant clauses and flag compliance gaps

---

## Known Issues

| Issue | Status | Workaround |
|-------|--------|-----------|
| `POST /api/chat` returns 504 for documents >100 pages | Timeout too short | Increase `TIMEOUT` env var or split document manually |
| Voice-to-text fails in Safari | Web Speech API not fully supported | Use Chrome/Edge for voice features |
| Stripe webhook delivery may arrive out of order | Stripe at-least-once delivery | Idempotency keys handled, but verify order in webhook handler |
| Large clause extraction (>50 clauses) truncates response | Token limit on LLM output | Extract in batches by clause type |
