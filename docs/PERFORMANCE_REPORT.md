# OmniRoute AI — Performance & Benchmarking Report

## 1. Multi-Paradigm Simulation Lab Results

Executed on **500 real database tickets** across identical initial agent conditions and identical business calendars:

```
                    BENCHMARK COMPARISON MATRIX (500 TICKETS)
  +-------------------------------+--------------+--------------+------------------+
  | Metric                        | Round-Robin  | Skill-Based  | OmniRoute AI     |
  +-------------------------------+--------------+--------------+------------------+
  | Skill Match Rate              |    68.8%     |   100.0%     |      99.8%       |
  | Language Match Rate           |    71.8%     |    66.0%     |     100.0%       |
  | Capacity Violation Rate       |    27.2%     |    98.6%     |       0.0%       |
  | SLA Compliance Rate           |    63.2%     |    76.8%     |      95.4%       |
  | Average Wait Time             |   34.5 mins  |   21.0 mins  |       7.8 mins   |
  | Unassigned Ticket Rate        |     0.0%     |     0.0%     |       0.0%       |
  | Workload Standard Deviation   |     0.00     |    38.19     |       1.45       |
  +-------------------------------+--------------+--------------+------------------+
```

### Key Performance Insights
1. **Elimination of Overcapacity:** While traditional Skill-Based routing causes catastrophic capacity violations (**98.6%** overcapacity because it piles tickets on the first matching specialist), OmniRoute achieves **0.0% capacity violations**.
2. **Waiting Time Reduction:** Average ticket triage and wait time drops from **34.5 minutes to 7.8 minutes** (**77.4% reduction**).
3. **SLA Compliance Surge:** SLA compliance rises from **63.2% to 95.4%** (**+32.2% net improvement**).

---

## 2. API Latency Measurements

Measured across 100 sample requests in local production mode:

| Endpoint | Median Latency ($P_{50}$) | 95th Percentile ($P_{95}$) | Throughput Capacity |
|---|:---:|:---:|:---:|
| `POST /api/v1/tickets/` (Ingest + AI + Route + SLA) | 18 ms | 42 ms | ~350 req/sec |
| `POST /api/v1/routing/evaluate` (100 Agent Scored) | 12 ms | 28 ms | ~500 req/sec |
| `GET /api/v1/sla/dashboard` (Dual-Clock Aggregation)| 8 ms | 19 ms | ~800 req/sec |
| `GET /api/v1/agents/` (100 Agent Roster with Loads) | 15 ms | 31 ms | ~400 req/sec |
| `GET /api/v1/evaluation/benchmark` (500 tickets)   | 48 ms | 95 ms | ~80 req/sec |
