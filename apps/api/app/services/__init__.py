"""Application services layer.

Services coordinate between:
- API routes (receive requests)
- Domain logic (business rules)
- Repositories (data access)
- External systems (LLMs, tools)

Services must not:
- Expose SQLAlchemy models in return types
- Hold database sessions across async waits
- Access database directly (use repositories)
"""
