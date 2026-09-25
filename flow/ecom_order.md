
Sync Ecom Order

Flow:

MariaDB
    |
    | order_ecom.sql
    ↓
Python
    |
    ↓
staging.stg_inform_ecom_order_line
    |
    ↓
Check duplicate
    |
    ↓
Delete duplicate in public
    |
    ↓
Insert new data
    |
    ↓
public.ecom_order_final