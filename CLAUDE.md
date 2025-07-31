# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**KMS-SFDC FAISS Vector Database for Cognate AI Integration**

This is a 14-week milestone-driven project to replace Coveo API2 lexical search in HPE's Cognate AI system with a FAISS-based semantic vector search. The primary goal is to build a vector database from 2 years of Pan-HPE SFDC case data, CFIs, and other engineer sources to enable the KM Generation Agent to perform superior case similarity search.

## Project Structure

```
KMS-SFDC/
├── src/
│   ├── data_extraction/    # SFDC + CFI data extraction
│   ├── vectorization/      # Nomic + FAISS vector DB
│   ├── search/            # Cognate AI integration API
│   └── utils/             # Configuration and processing
├── config/               # Project configuration
├── scripts/              # Build and deployment scripts
├── tests/                # Unit and integration tests
├── input/                # Project requirements
│   ├── problemstmt.txt   # Detailed requirements
│   └── KMS_v1.7.pptx    # Project presentation
└── data/                 # Generated FAISS indexes
```

## Key Project Milestones (14 weeks)

**Week 2: Field Finalization**
- AC: GSR sign-off on vectorization fields
- Determine which SFDC case fields to include
- Define CFI and other engineer source integration

**Week 4: Initial Vectorization** 
- AC: Showcase random case details vectorization
- Process 2 years of SFDC case data with Nomic embeddings
- Generate FAISS index file

**Week 6: Test Data Creation**
- AC: GSR sign-off on test data
- Create accuracy measurement dataset with GSR/DE

**Week 8: Accuracy Measurement**
- AC: GSR sign-off on accepted accuracy level
- Measure vector search accuracy vs test data
- Iterate on vectorization approach

**Week 10: Cognate AI Integration**
- AC: Unit/fitness/regression tests success
- Replace Coveo API2 with FAISS vector search
- Maintain existing KM Generation Agent functionality

**Week 12: Pipeline Creation**
- AC: SRE/Security sign-off, demo update
- Jenkins scheduled vectorization pipeline
- Monitoring, alerting, and compliance

**Week 14: ITG/PRO Deployment**
- AC: KM Generation Agent calls updated vectorDB
- Production deployment replacing Coveo search
- Full Cognate AI integration verification

## Technology Stack

- **Vector Database**: FAISS (Facebook AI Similarity Search)
- **Embeddings**: Nomic embed-text-v1.5 (local execution, 768 dimensions)
- **Data Sources**: SFDC case data, CFIs, engineer sources
- **Integration**: Cognate AI KM Generation Agent
- **Pipeline**: Jenkins scheduled jobs
- **Deployment**: ITG/PRO environments
- **Language**: Python with FastAPI

## Data Model

**Primary Sources:**
- 2 years Pan-HPE SFDC case data
- CFIs (Customer Facing Information) 
- Other engineer-used sources (GSR defined)

**Key Fields for Vectorization:**
- Subject: Case headline
- Description: Problem description  
- Resolution__c: Solution details
- Case_Notes__c: Additional troubleshooting notes

**Exclusions:**
- KM articles already in Coveo

## Development Commands

```bash
# Setup and test
make setup-env          # Environment setup with Nomic
make test-embeddings    # Test local Nomic embeddings
make build-index-sample # Build test FAISS index
make run-api           # Start Cognate AI integration API

# Development
make test              # Run all tests
make lint              # Code quality checks
make format            # Code formatting
```

## Key Stakeholders & Approvals

- **GSR**: Primary stakeholder for field selection, test data, accuracy sign-off
- **DE**: Data engineering collaboration for field finalization
- **SRE/Security**: Pipeline and deployment approvals
- **SMART**: NFR alignment and monitoring requirements
- **Cognate AI Team**: Integration requirements and testing

## Integration Notes

**Replacing Coveo API2:**
- Current: Lexical search via Coveo API2
- New: Semantic vector search via FAISS
- Target: KM Generation Agent in Cognate AI
- Requirement: Maintain all existing functionalities

**API Compatibility:**
- Design API endpoints to match Cognate AI expectations
- Ensure response format compatibility
- Provide fallback mechanisms if needed

## Critical Success Factors

1. **GSR Approval**: All milestones require GSR sign-off
2. **Accuracy Standards**: Must meet or exceed current Coveo performance
3. **Integration Seamless**: No functionality loss in Cognate AI
4. **Performance**: Fast vector search for real-time use
5. **Compliance**: Meet SRE, Security, and NFR requirements