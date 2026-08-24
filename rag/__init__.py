"""
rag/ — RAG pipeline bileşenleri

Bu modül şu bileşenleri içerir:
  - embedder.py   : Metin → embedding vektörü
  - retriever.py  : Sorgu → ilgili chunk'lar
  - generator.py  : Chunk'lar + sorgu → LLM cevabı
  - pipeline.py   : Tüm pipeline'ı orkestre eder
"""
