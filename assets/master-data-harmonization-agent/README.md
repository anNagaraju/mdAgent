# Master Data Harmonization Agent

An AI agent that profiles master data, detects duplicate Business Partner and Product records, computes golden records, and executes approved merges via SAP S/4HANA APIs

## Overview

Uses A2A Protocol, LangGraph, LiteLLM, and SAP Cloud SDK.

## Structure

- `app/main.py` - A2A server entry
- `app/agent_executor.py` - Request handling
- `app/agent.py` - Agent logic
