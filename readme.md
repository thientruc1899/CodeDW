#  Sync Flow

## 1. Project Structure

```text
project/
│
├── helper/
│   └── class_resource.py
│       # Database connection
│       # Pull data by parameter
│       # Insert data into PostgreSQL
│
├── sql/
│   ├── create_stag_table.sql
│   ├── extract_data.sql
│   └── load_fact_data.sql
│
├── sync_inform_order.py
│   # Main orchestration
│
└── .env
    # Database credentials
```



## 2. class_resource Logic

`class_resource.py` is the shared resource layer between the sync script and databases.

```text
                 class_resource.py
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
           MariaDB              PostgreSQL
          (Source)              (Staging)
              │                     ▲
              │                     │
              └── pull_by_date() ───┤
                                    │
                             insert_postgres()
```

### Main Responsibilities

**`connect()`**

Creates database connections once at the beginning of the sync process.

```text
.env
  │
  ├── INFORM_* ──► MariaDB
  │
  └── DW_* ──────► PostgreSQL
```

**`pull_by_date(sql, target_date)`**

Receives SQL from the orchestration layer and executes it against MariaDB using `target_date` as a parameter.

```text
SQL file
   +
target_date
   │
   ▼
pull_by_date()
   │
   ▼
MariaDB
   │
   ▼
List of rows
```

**`insert_postgres(rows, schema, table)`**

Receives extracted rows and inserts them into the PostgreSQL RAW staging table.

RAW staging uses an **append-only** strategy:

- Existing records are not updated.
- Existing records are not deleted.
- Duplicate source `id` values are allowed.
- Every sync inserts a new copy of the extracted source record.
- `loaded_at` records when the row was loaded into PostgreSQL.

**`close()`**

Closes both MariaDB and PostgreSQL connections after all sync jobs have completed.

---

## 3. Main Sync Flow

`sync_inform_ecom.py` controls the execution order.

```text
                    sync_inform_ecom.py
                            │
                            ▼
                     Resource()
                            │
                            ▼
                       connect()
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
      ecom_order.sql              ecom_order_detail.sql
             │                             │
             ▼                             ▼
      pull_by_date()               pull_by_date()
             │                             │
             ▼                             ▼
   MariaDB ecom_order         MariaDB ecom_order_detail
             │                             │
             ▼                             ▼
     insert_postgres()            insert_postgres()
             │                             │
             ▼                             ▼
stg_inform_ecom_order    stg_inform_ecom_order_detail
             │                             │
             └──────────────┬──────────────┘
                            │
                            ▼
                         close()
```

## 4. Execution Sequence

```text
START
  │
  ▼
Load .env
  │
  ▼
Create Resource
  │
  ▼
Connect MariaDB + PostgreSQL
  │
  ├─────────────────────────────────────┐
  │                                     │
  ▼                                     ▼
Load ecom_order.sql          Load ecom_order_detail.sql
  │                                     │
  ▼                                     ▼
Pull order by date           Pull order_detail by date
  │                                     │
  ▼                                     ▼
Insert into                  Insert into
stg_inform_ecom_order        stg_inform_ecom_order_detail
  │                                     │
  └──────────────────┬──────────────────┘
                     │
                     ▼
              Close connections
                     │
                     ▼
                    END
```

## 5. Data Flow

```mermaid
flowchart LR

    A["sync_inform_ecom.py"]

    B["class_resource.py"]

    C["ecom_order.sql"]
    D["ecom_order_detail.sql"]

    E[("MariaDB")]

    F["stg_inform_ecom_order"]
    G["stg_inform_ecom_order_detail"]

    H[("PostgreSQL")]

    A --> B

    C --> A
    D --> A

    B -->|connect| E
    B -->|connect| H

    A -->|SQL + target_date| B

    B -->|pull_by_date| E

    E -->|order rows| B
    E -->|order_detail rows| B

    B -->|insert_postgres| F
    B -->|insert_postgres| G

    F --> H
    G --> H
```

## 6. Design Principle

The responsibilities are separated into three layers:

```text
SQL Layer
   │
   │ Defines WHAT data to extract
   ▼
sql/*.sql

Resource Layer
   │
   │ Defines HOW to connect, pull and insert
   ▼
helper/class_resource.py

Orchestration Layer
   │
   │ Defines WHEN and IN WHAT ORDER jobs run
   ▼
sync_inform_ecom.py
```

This separation keeps database handling reusable while allowing each SQL query to be maintained independently.

## 8. Overall Architecture

```text
                        .env
                          │
                          ▼
                 class_resource.py
                ┌─────────┴─────────┐
                ▼                   ▼
             MariaDB            PostgreSQL
                ▲                   ▲
                │                   │
        pull_by_date()       insert_postgres()
                ▲                   ▲
                │                   │
                └──── sync_inform_ecom.py
                           ▲
                     ┌─────┴─────┐
                     │           │
              ecom_order.sql  ecom_order_detail.sql
```

### Core Rule

> `sync_inform_ecom.py` orchestrates the job.  
> `sql/` defines the extraction logic.  
> `class_resource.py` handles database resources and reusable database operations.  
> RAW staging tables remain append-only.