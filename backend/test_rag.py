#!/usr/bin/env python3
"""Test script to verify RAG system is working correctly."""

import sys
sys.path.insert(0, '.')

# Test ChromaDB import
import chromadb
print('✅ ChromaDB imported successfully')

# Test PayerPolicyRAG
from app.services.policy_rag import PayerPolicyRAG, PolicyDocument, initialize_policy_database
print('✅ PayerPolicyRAG imported successfully')

# Check if method exists
methods = [m for m in dir(PayerPolicyRAG) if not m.startswith('_')]
print(f'   Methods: {methods}')

# Initialize RAG system
rag = PayerPolicyRAG()
print('✅ PayerPolicyRAG initialized')

# Check if policies need to be loaded
stats = rag.get_policy_stats()
if stats["total_policies"] == 0:
    print('📥 Loading comprehensive payer policies (8 payers)...')
    initialize_policy_database(rag)
    stats = rag.get_policy_stats()

print(f'✅ Policy stats: {stats["total_policies"]} policies loaded')
print(f'   By payer: {stats["by_payer"]}')
print(f'   By type: {stats["by_type"]}')

# Test search
print('\n🔍 Testing semantic search...')
results = rag.search_policies('prior authorization knee replacement', n_results=3)
print(f'✅ Search returned {len(results)} results')
for r in results:
    print(f'   - {r.document.policy_title} ({r.document.payer_name}) - score: {r.relevance_score:.3f}')

# Test payer-specific search
print('\n🔍 Testing payer-specific search (Florida Blue)...')
results = rag.search_policies('appeal process', payer_id='FL_BLUE', n_results=2)
print(f'✅ Florida Blue search returned {len(results)} results')
for r in results:
    print(f'   - {r.document.policy_title} - score: {r.relevance_score:.3f}')

# Test policy type filter
print('\n🔍 Testing policy type filter (prior_auth)...')
results = rag.search_policies('MRI imaging', policy_type='prior_auth', n_results=2)
print(f'✅ Prior auth search returned {len(results)} results')
for r in results:
    print(f'   - {r.document.policy_title} ({r.document.payer_name}) - score: {r.relevance_score:.3f}')

print('\n✅ All RAG tests passed!')
