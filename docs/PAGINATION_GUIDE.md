# Pagination Guide

## Backend

Vehicle and parking-history endpoints support:

- `page` — 1-based current page
- `page_size` — 1–100 records
- `paginated=true` — returns a paginated object

Paginated response:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 25,
  "total_pages": 0
}
```

Without `paginated=true`, existing list behavior remains available for backward compatibility.

## Frontend

Vehicles and Parking History show page controls, page-size selection, total counts, loading, empty, error, and retry states.

## Slots

`/slots/?paginated=true&page=1&page_size=200` returns the same metadata shape and an `items` array.
