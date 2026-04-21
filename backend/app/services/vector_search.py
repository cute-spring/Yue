import sqlite3
import sqlite_vec
from typing import List, Dict, Any, Optional
from app.core.database import DB_FILE
import json


class VectorSearchService:
    """Vector search service using sqlite-vec for semantic search"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_FILE

    def extension_loading_supported(self) -> bool:
        probe = sqlite3.connect(":memory:")
        try:
            return hasattr(probe, "enable_load_extension") and hasattr(probe, "load_extension")
        finally:
            probe.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with sqlite-vec loaded"""
        if not self.extension_loading_supported():
            raise RuntimeError("sqlite extension loading is not supported by this Python sqlite3 build")
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn
    
    def search_similar_messages(
        self,
        query_embedding: List[float],
        limit: int = 10,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for messages similar to the query embedding
        
        Args:
            query_embedding: The query vector (e.g., from OpenAI embeddings)
            limit: Maximum number of results to return
            session_id: Optional session ID to filter results
            
        Returns:
            List of messages with similarity scores
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Build query
            if session_id:
                query = """
                    SELECT 
                        id,
                        session_id,
                        role,
                        content,
                        timestamp,
                        vec_distance_cosine(embedding, ?) as distance
                    FROM messages
                    WHERE embedding IS NOT NULL
                      AND session_id = ?
                    ORDER BY distance
                    LIMIT ?
                """
                params = (json.dumps(query_embedding), session_id, limit)
            else:
                query = """
                    SELECT 
                        id,
                        session_id,
                        role,
                        content,
                        timestamp,
                        vec_distance_cosine(embedding, ?) as distance
                    FROM messages
                    WHERE embedding IS NOT NULL
                    ORDER BY distance
                    LIMIT ?
                """
                params = (json.dumps(query_embedding), limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'session_id': row[1],
                    'role': row[2],
                    'content': row[3],
                    'timestamp': row[4],
                    'distance': row[5],
                    'similarity': 1 - row[5]  # Convert distance to similarity
                })
            
            return results
        finally:
            conn.close()
    
    def store_embedding(
        self,
        message_id: int,
        embedding: List[float]
    ) -> None:
        """
        Store embedding vector for a message
        
        Args:
            message_id: The message ID to update
            embedding: The embedding vector to store
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE messages SET embedding = ? WHERE id = ?",
                (json.dumps(embedding), message_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    def verify_vector_support(self) -> bool:
        """Verify that sqlite-vec is properly loaded and working"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Test vector distance function
            test_vec1 = [0.1, 0.2, 0.3]
            test_vec2 = [0.1, 0.2, 0.4]
            
            cursor.execute(
                "SELECT vec_distance_cosine(?, ?)",
                (json.dumps(test_vec1), json.dumps(test_vec2))
            )
            result = cursor.fetchone()
            
            return result is not None and result[0] >= 0
        except Exception as e:
            print(f"Vector support verification failed: {e}")
            return False
        finally:
            conn.close()
    
    def get_vector_stats(self) -> Dict[str, Any]:
        """Get statistics about vector embeddings in the database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Count messages with embeddings
            cursor.execute("SELECT COUNT(*) FROM messages WHERE embedding IS NOT NULL")
            total_with_embeddings = cursor.fetchone()[0]
            
            # Count total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            return {
                'total_messages': total_messages,
                'messages_with_embeddings': total_with_embeddings,
                'coverage_percentage': (total_with_embeddings / total_messages * 100) if total_messages > 0 else 0
            }
        finally:
            conn.close()


# Singleton instance
_vector_search_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """Get or create the vector search service instance"""
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService()
    return _vector_search_service
