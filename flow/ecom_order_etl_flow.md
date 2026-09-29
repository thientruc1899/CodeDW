# E-commerce Order ETL Flow

``` mermaid
flowchart LR
    subgraph S["1. SOURCE (MariaDB)"]
        O["ecom_order"]
        D["ecom_order_detail"]
    end

    subgraph R["2. STAGING RAW (append-only)"]
        RO["stg_inform_ecom_order<br/><br/>• Append-only (keep full history)<br/>• No PRIMARY KEY<br/>• New records inserted on each sync<br/>• Multiple rows per id allowed<br/>• Has loaded_at column"]
        RD["stg_inform_ecom_order_detail<br/><br/>• Append-only (keep full history)<br/>• No PRIMARY KEY<br/>• New records inserted on each sync<br/>• Multiple rows per id allowed<br/>• Has loaded_at column"]
    end

    subgraph F["3. FINAL SNAPSHOT (1 row per id)"]
        FO["final_inform_ecom_order<br/><br/>• 1 most recent row per id<br/>• Based on updated_at DESC<br/>• Tie-breaker: loaded_at DESC"]
        FD["final_inform_ecom_order_detail<br/><br/>• 1 most recent row per id<br/>• Based on loaded_at DESC"]
    end

    subgraph B["4. FACT TABLE (Join FINAL tables)"]
        BF["fact_ecom_order<br/>(fact / analytic table)<br/><br/>• Join final_inform_ecom_order + final_inform_ecom_order_detail<br/>• Apply business logic for calculations<br/>• Used for reporting and analysis"]
    end

    O -->|"ETL (Python)<br/>filter by date"| RO
    D -->|"ETL (Python)<br/>filter by date"| RD
    RO -->|"Transform<br/>latest row per id"| FO
    RD -->|"Transform<br/>latest row per id"| FD
    FO --> BF
    FD --> BF
```

## Flow Summary

| Layer | Table | Purpose |
|---|---|---|
| Source | `ecom_order`<br>`ecom_order_detail` | Order source data in MariaDB |
| Staging | `stg_inform_ecom_order`<br>`stg_inform_ecom_order_detail` | Append-only order history<br>Duplicate `id` values are allowed |
| Final Snapshot | `final_inform_ecom_order`<br>`final_inform_ecom_order_detail` | Latest order record per `id`, using `updated_at DESC`, then `loaded_at DESC`<br>Latest order-detail record per `id`, using `loaded_at DESC` |
| Fact | `stg_ecom_order_final` | Join the two FINAL tables and apply business logic |


## Processing Logic

**Source → Staging:** Python ETL extracts records from MariaDB by date and
inserts them into Staging. RAW tables are append-only, so existing
records are not updated or deleted.

**Staging → Final:** Deduplicate each RAW table independently. The order
snapshot keeps the newest record by `updated_at`, with `loaded_at` as
the tie-breaker. The order-detail snapshot keeps the newest record by
`loaded_at`.

**Final → Fact:** Join `final_inform_ecom_order` with
`final_inform_ecom_order_detail`, then apply revenue, quantity,
channel mapping, and other business rules to build
`fact_ecom_order`.

