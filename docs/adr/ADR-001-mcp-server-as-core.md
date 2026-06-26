# ADR-001 — MCP Server as the Core Product

**Date:** 2026-06-26  
**Status:** Accepted

## Context

The project goal is to demonstrate real-world use of the MCP protocol for lab diagnostics. A decision was needed on whether to build a standalone CLI tool, a REST API, or an MCP server.

## Decision

The MCP server is the primary artifact. The OpenAI CLI client is a secondary example of consumption. All diagnostic logic lives in the server; the client is interchangeable.

## Consequences

- The server must be runnable independently of any AI client
- Tools, Resources, and Prompts must all be implemented to showcase the full protocol
- The CLI client using OpenAI GPT-4o serves as a demo, not the product
- Future clients (Claude Desktop, Cursor, custom agents) can connect without changes to the server
