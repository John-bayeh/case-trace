"""Simulated hospital information system.

This module provides:
- Clinical data storage and retrieval
- FHIR-inspired resource APIs
- Document and asset management
- Patient/encounter navigation

Architecture:
    Hospital API
         ↓
    Hospital Service
         ↓
    Clinical Repository
         ↓
    SQLAlchemy Models
         ↓
    SQLite Database

Agents access this through the tool layer, not directly.
"""
