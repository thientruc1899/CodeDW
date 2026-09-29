# E-commerce Order ETL Flow

``` mermaid
flowchart LR
    subgraph S["1. SOURCE (MariaDB)"]
        O["ecom_order<br/>(orders)"]
        D["ecom_order_detail<br/>(order details)"]
    end

    subgraph R["2. RAW STAGING (append-only)"]
        RO["stg_inform_ecom_order<br/><br/>• Append-only (keep full history)<br/>• No PRIMARY KEY<br/>• New records inserted on each sync<br/>• Multiple rows per id allowed<br/>• Has loaded_at column"]
        RD["stg_inform_ecom_order_detail<br/><br/>• Append-only (keep full history)<br/>• No PRIMARY KEY<br/>• New records inserted on each sync<br/>• Multiple rows per id allowed<br/>• Has loaded_at column"]
    end

    subgraph F["3. FINAL SNAPSHOT (1 row per id)"]
        FO["final_inform_ecom_order<br/><br/>• 1 most recent row per id<br/>• Based on updated_at DESC<br/>• Tie-breaker: loaded_at DESC"]
        FD["final_inform_ecom_order_detail<br/><br/>• 1 most recent row per id<br/>• Based on loaded_at DESC"]
    end

    subgraph B["4. BUSINESS / FACT TABLE (Join FINAL tables)"]
        BF["fact_ecom_order<br/>(fact / analytic table)<br/><br/>• Join final_inform_ecom_order + final_inform_ecom_order_detail<br/>• Apply business logic for calculations<br/>• Revenue, quantity, channel mapping, etc.<br/>• Used for reporting and analysis"]
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
| Source | `ecom_order` | Order source data in MariaDB |
| Source | `ecom_order_detail` | Order-detail source data in MariaDB |
| RAW Staging | `stg_inform_ecom_order` | Append-only order history; duplicate `id` values are allowed |
| RAW Staging | `stg_inform_ecom_order_detail` | Append-only order-detail history; duplicate `id` values are allowed |
| Final Snapshot | `final_inform_ecom_order` | Latest order record per `id`, using `updated_at DESC`, then `loaded_at DESC` |
| Final Snapshot | `final_inform_ecom_order_detail` | Latest order-detail record per `id`, using `loaded_at DESC` |
| Business / Fact | `stg_ecom_order_final` | Join the two FINAL tables and apply business logic |

  --------------------------------------------------------------------------------------

## Processing Logic

**Source → RAW:** Python ETL extracts records from MariaDB by date and
inserts them into RAW staging. RAW tables are append-only, so existing
records are not updated or deleted.

**RAW → FINAL:** Deduplicate each RAW table independently. The order
snapshot keeps the newest record by `updated_at`, with `loaded_at` as
the tie-breaker. The order-detail snapshot keeps the newest record by
`loaded_at`.

**FINAL → BUSINESS / FACT:** Join `final_inform_ecom_order` with
`final_inform_ecom_order_detail`, then apply revenue, quantity,
channel mapping, and other business rules to build
`fact_ecom_order`.
