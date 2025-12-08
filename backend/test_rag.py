#!/usr/bin/env python3
"""Test script to verify RAG system is working correctly with all 9 payers."""

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
    print('📥 Loading comprehensive payer policies (9 payers)...')
    initialize_policy_database(rag)
    stats = rag.get_policy_stats()

print(f'✅ Policy stats: {stats["total_policies"]} policies loaded')
print(f'   By payer: {stats["by_payer"]}')
print(f'   By type: {stats["by_type"]}')

# Verify all 9 payers are loaded
expected_payers = ['FL_BLUE', 'HUMANA_FL', 'FL_MEDICAID', 'AETNA_FL', 'MEDICARE', 'UNITED', 'CIGNA', 'TRICARE', 'ANTHEM']
loaded_payers = list(stats["by_payer"].keys())
print(f'\n📋 Verifying all 9 payers loaded...')
for payer in expected_payers:
    if payer in loaded_payers:
        print(f'   ✅ {payer}: {stats["by_payer"][payer]} policies')
    else:
        print(f'   ❌ {payer}: NOT LOADED')

# Test search for each payer
print('\n🔍 Testing semantic search for each payer...')
for payer in expected_payers:
    results = rag.search_policies('prior authorization', payer_id=payer, n_results=1)
    if results:
        print(f'   ✅ {payer}: Found "{results[0].document.policy_title}"')
    else:
        print(f'   ⚠️ {payer}: No results for "prior authorization"')

# Test general semantic search
print('\n🔍 Testing general semantic search...')
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

# Test Anthem/BCBS search (new payer)
print('\n🔍 Testing Anthem/BCBS search...')
results = rag.search_policies('orthopedic surgery', payer_id='ANTHEM', n_results=2)
print(f'✅ Anthem search returned {len(results)} results')
for r in results:
    print(f'   - {r.document.policy_title} - score: {r.relevance_score:.3f}')

# Test policy type filter
print('\n🔍 Testing policy type filter (prior_auth)...')
results = rag.search_policies('MRI imaging', policy_type='prior_auth', n_results=2)
print(f'✅ Prior auth search returned {len(results)} results')
for r in results:
    print(f'   - {r.document.policy_title} ({r.document.payer_name}) - score: {r.relevance_score:.3f}')

# Test appeal procedures filter
print('\n🔍 Testing policy type filter (appeal_procedures)...')
results = rag.search_policies('deadline', policy_type='appeal_procedures', n_results=2)
print(f'✅ Appeal procedures search returned {len(results)} results')
for r in results:
    print(f'   - {r.document.policy_title} ({r.document.payer_name}) - score: {r.relevance_score:.3f}')

# Summary
print('\n' + '='*60)
print('📊 RAG SYSTEM TEST SUMMARY')
print('='*60)
print(f'Total Payers: {len(loaded_payers)}')
print(f'Total Policies: {stats["total_policies"]}')
print(f'Expected Payers: {len(expected_payers)}')
all_payers_loaded = all(p in loaded_payers for p in expected_payers)
print(f'All Payers Loaded: {"✅ YES" if all_payers_loaded else "❌ NO"}')
print('='*60)

if all_payers_loaded and stats["total_policies"] >= 25:
    print('\n✅ All RAG tests passed!')
else:
    print('\n❌ Some RAG tests failed - check output above')
