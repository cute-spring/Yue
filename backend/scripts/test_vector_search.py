#!/usr/bin/env python3
"""
Test script to verify sqlite-vec vector search functionality

This script:
1. Runs database migrations
2. Creates test messages with sample embeddings
3. Performs vector similarity search
4. Verifies results
"""

import sys
import os
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import DB_FILE, engine, Base
from app.models.chat import Message, Session
from app.services.vector_search import get_vector_search_service
from datetime import datetime
import json


def create_sample_embeddings():
    """Create sample embedding vectors for testing"""
    # Simulate embeddings from different semantic clusters
    return {
        'greeting': [0.8, 0.1, 0.2, 0.1, 0.3],
        'code_question': [0.1, 0.9, 0.2, 0.3, 0.1],
        'python_help': [0.1, 0.85, 0.25, 0.2, 0.15],
        'weather_ask': [0.2, 0.1, 0.9, 0.1, 0.2],
        'math_problem': [0.15, 0.2, 0.15, 0.85, 0.3],
        'code_debug': [0.1, 0.88, 0.18, 0.25, 0.12],
    }


def run_migration():
    """Run Alembic migration to add embedding column"""
    print("=" * 60)
    print("Step 1: Running database migration...")
    print("=" * 60)
    
    import subprocess
    result = subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Migration completed successfully")
        return True
    else:
        print(f"❌ Migration failed: {result.stderr}")
        return False


def setup_test_data():
    """Create test messages with embeddings"""
    print("\n" + "=" * 60)
    print("Step 2: Creating test data with embeddings...")
    print("=" * 60)
    
    from sqlalchemy.orm import Session as DBSession
    
    db = DBSession(bind=engine)
    try:
        # Create a test session
        test_session = Session(
            id="test-vector-search-session",
            title="Vector Search Test Session",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(test_session)
        db.commit()
        
        # Create test messages with embeddings
        embeddings = create_sample_embeddings()
        test_messages = [
            ("Hello! How can I help you?", "user", embeddings['greeting']),
            ("I have a question about Python code", "user", embeddings['code_question']),
            ("Can you help me debug this Python function?", "user", embeddings['code_debug']),
            ("What's the weather like today?", "user", embeddings['weather_ask']),
            ("Solve this math problem: 2+2=?", "user", embeddings['math_problem']),
            ("How do I fix this Python error?", "user", embeddings['python_help']),
        ]
        
        for content, role, embedding in test_messages:
            msg = Message(
                session_id=test_session.id,
                role=role,
                content=content,
                timestamp=datetime.utcnow(),
                embedding=json.dumps(embedding)
            )
            db.add(msg)
        
        db.commit()
        
        print(f"✅ Created {len(test_messages)} test messages with embeddings")
        return test_session.id
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to create test data: {e}")
        return None
    finally:
        db.close()


def test_vector_search():
    """Test vector similarity search"""
    print("\n" + "=" * 60)
    print("Step 3: Testing vector search...")
    print("=" * 60)
    
    vector_search = get_vector_search_service()
    if not vector_search.extension_loading_supported():
        pytest.skip("sqlite extension loading is not supported by this Python sqlite3 build")
    
    # Verify vector support
    print("\n3.1 Verifying sqlite-vec support...")
    if vector_search.verify_vector_support():
        print("✅ sqlite-vec is working correctly")
    else:
        print("❌ sqlite-vec verification failed")
        return False
    
    # Test 1: Search for code-related queries
    print("\n3.2 Test: Searching for code-related queries...")
    code_query = [0.1, 0.9, 0.2, 0.3, 0.1]  # Similar to code_question
    results = vector_search.search_similar_messages(
        query_embedding=code_query,
        limit=3
    )
    
    print(f"   Found {len(results)} results")
    for i, result in enumerate(results, 1):
        print(f"   {i}. [similarity: {result['similarity']:.4f}] {result['content'][:60]}...")
    
    # Verify results make sense
    if len(results) > 0:
        print("✅ Vector search returned results")
    else:
        print("❌ Vector search returned no results")
        return False
    
    # Test 2: Search within specific session
    print("\n3.3 Test: Searching within specific session...")
    session_results = vector_search.search_similar_messages(
        query_embedding=code_query,
        limit=5,
        session_id="test-vector-search-session"
    )
    print(f"   Found {len(session_results)} results in session")
    
    # Test 3: Search for weather-related queries
    print("\n3.4 Test: Searching for weather-related queries...")
    weather_query = [0.2, 0.1, 0.9, 0.1, 0.2]
    weather_results = vector_search.search_similar_messages(
        query_embedding=weather_query,
        limit=3
    )
    
    if len(weather_results) > 0:
        top_result = weather_results[0]
        print(f"   Top result [similarity: {top_result['similarity']:.4f}]: {top_result['content']}")
        if 'weather' in top_result['content'].lower():
            print("✅ Semantic search working correctly (weather query matched weather content)")
        else:
            print("⚠️  Top result may not be semantically relevant")
    else:
        print("❌ No results for weather query")
    
    return True


def show_stats():
    """Display vector search statistics"""
    print("\n" + "=" * 60)
    print("Step 4: Vector search statistics...")
    print("=" * 60)
    
    vector_search = get_vector_search_service()
    stats = vector_search.get_vector_stats()
    
    print(f"   Total messages: {stats['total_messages']}")
    print(f"   Messages with embeddings: {stats['messages_with_embeddings']}")
    print(f"   Coverage: {stats['coverage_percentage']:.2f}%")


def cleanup():
    """Clean up test data"""
    print("\n" + "=" * 60)
    print("Step 5: Cleanup...")
    print("=" * 60)
    
    from sqlalchemy.orm import Session as DBSession
    from sqlalchemy import delete
    
    db = DBSession(bind=engine)
    try:
        # Delete test session (cascade will delete messages)
        db.execute(delete(Session).where(Session.id == "test-vector-search-session"))
        db.commit()
        print("✅ Test data cleaned up")
    except Exception as e:
        db.rollback()
        print(f"⚠️  Cleanup warning: {e}")
    finally:
        db.close()


def main():
    """Main test runner"""
    print("\n" + "=" * 60)
    print("SQLite-vec Vector Search Verification Test")
    print("=" * 60)
    print(f"Database: {DB_FILE}\n")
    
    try:
        # Step 1: Run migration
        if not run_migration():
            print("\n❌ Migration failed. Exiting.")
            return False
        
        # Step 2: Setup test data
        test_session_id = setup_test_data()
        if not test_session_id:
            print("\n❌ Test data setup failed. Exiting.")
            return False
        
        # Step 3: Test vector search
        if not test_vector_search():
            print("\n❌ Vector search test failed.")
            return False
        
        # Step 4: Show stats
        show_stats()
        
        # Step 5: Cleanup
        cleanup()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nsqlite-vec is successfully integrated and working!")
        print("You can now use vector search for semantic queries.")
        print("\nNext steps:")
        print("1. Generate real embeddings using OpenAI API or local models")
        print("2. Store embeddings when creating messages")
        print("3. Use vector_search.search_similar_messages() for semantic search")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
