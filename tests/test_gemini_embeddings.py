#!/usr/bin/env python3
"""
Test Gemini Embeddings API
==========================
Verify Gemini embedding model connectivity and functionality.

Usage:
    python test_gemini_embeddings.py
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def test_with_google_genai():
    """Test using google-generativeai library"""
    try:
        import google.generativeai as genai
    except ImportError:
        print("❌ google-generativeai not installed")
        print("   Run: pip install google-generativeai")
        return False
    
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not set in .env")
        return False
    
    print(f"🔑 API Key: {GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-4:]}")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Test embedding
    test_text = "This is a test document for Open WebUI RAG functionality."
    
    print(f"\n📝 Test text: \"{test_text}\"")
    print("🔄 Generating embedding...")
    
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=test_text,
            task_type="retrieval_document"
        )
        
        embedding = result['embedding']
        
        print(f"\n✅ Embedding generated successfully!")
        print(f"   Dimension: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
        print(f"   Last 5 values: {embedding[-5:]}")
        
        # Test query embedding
        query = "What is RAG?"
        result_query = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        
        print(f"\n✅ Query embedding also works!")
        print(f"   Query: \"{query}\"")
        print(f"   Dimension: {len(result_query['embedding'])}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error generating embedding: {e}")
        return False


def test_vietnamese():
    """Test Vietnamese text embedding"""
    try:
        import google.generativeai as genai
    except ImportError:
        return False
    
    if not GEMINI_API_KEY:
        return False
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    test_text_vi = "Đây là văn bản tiếng Việt để kiểm tra khả năng embedding."
    
    print(f"\n🇻🇳 Testing Vietnamese:")
    print(f"   Text: \"{test_text_vi}\"")
    
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=test_text_vi,
            task_type="retrieval_document"
        )
        
        print(f"   ✅ Vietnamese embedding works! Dimension: {len(result['embedding'])}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Gemini Embeddings API Test")
    print("=" * 60)
    
    success = test_with_google_genai()
    
    if success:
        test_vietnamese()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Gemini embeddings ready for Open WebUI.")
    else:
        print("❌ Tests failed. Please check your API key and network.")
    print("=" * 60)


if __name__ == "__main__":
    main()
