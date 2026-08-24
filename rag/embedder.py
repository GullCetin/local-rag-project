"""
rag/embedder.py — Embedding Modeli Wrapper
==========================================
Bu modül, Foundry Local SDK'nın embedding modelini yöneten
basit bir arayüz sağlar.

Neden ayrı modül?
  Embedding model yükleme maliyetlidir (RAM'e yükleme).
  Bu sınıf modeli bir kez yükleyip singleton olarak saklar;
  her embedding isteğinde yeniden yükleme yapılmaz.

Kullanım:
  embedder = Embedder()
  embedder.load()  # Bir kez çağır
  vector = embedder.embed("metin")
"""

import logging
from typing import Optional

from foundry_local_sdk import Configuration, FoundryLocalManager

from config import APP_NAME, EMBEDDING_MODEL_ALIAS

logger = logging.getLogger(__name__)


class Embedder:
    """
    Foundry Local embedding modelini yöneten sınıf.
    
    Neden singleton pattern?
    Model yükleme RAM'e yazmayı gerektirir; tekrar tekrar
    yüklemek hem yavaş hem de kaynak israfı olur.
    """

    def __init__(self) -> None:
        self._model = None
        self._client = None
        self._embedding_dim: Optional[int] = None
        self._is_loaded = False

    def load(self) -> None:
        """
        Embedding modelini indirir (gerekirse) ve RAM'e yükler.
        Bu metot uygulama başlangıcında bir kez çağrılmalıdır.
        """
        if self._is_loaded:
            logger.debug("Embedding modeli zaten yüklü, tekrar yükleme atlandı.")
            return

        logger.info(f"Foundry Local başlatılıyor (app: {APP_NAME})...")
        config = Configuration(app_name=APP_NAME)
        try:
            FoundryLocalManager.initialize(config)
        except Exception:
            # Singleton zaten başlatılmış (Streamlit cache clear sonrası olabilir)
            logger.debug("FoundryLocalManager zaten başlatılmış, devam ediliyor.")
        manager = FoundryLocalManager.instance

        logger.info(f"Embedding modeli aranıyor: '{EMBEDDING_MODEL_ALIAS}'")
        self._model = manager.catalog.get_model(EMBEDDING_MODEL_ALIAS)

        if self._model is None:
            raise RuntimeError(
                f"Embedding modeli '{EMBEDDING_MODEL_ALIAS}' katalogda bulunamadı. "
                f"Lütfen model adını config.py'den kontrol edin."
            )

        if not self._model.is_cached:
            logger.info(f"Model yerel diskte yok, indiriliyor...")
            def _progress(p: float) -> None:
                print(f"\r  İndiriliyor: %{round(p)}", end="", flush=True)
            self._model.download(_progress)
            print()  # Satır sonu

        logger.info("Embedding modeli RAM'e yükleniyor...")
        self._model.load()
        self._client = self._model.get_embedding_client()
        self._is_loaded = True
        logger.info("Embedding modeli hazır.")

    def embed(self, text: str) -> list[float]:
        """
        Verilen metni embedding vektörüne dönüştürür.

        Args:
            text: Embed edilecek metin

        Returns:
            Float listesi olarak embedding vektörü

        Raises:
            RuntimeError: Model henüz yüklenmemişse
        """
        if not self._is_loaded:
            raise RuntimeError(
                "Embedding modeli yüklenmemiş. Önce embedder.load() çağırın."
            )

        if not text or not text.strip():
            raise ValueError("Boş metin embed edilemez.")

        # SDK, OpenAI uyumlu CreateEmbeddingResponse döner.
        # Vektör .data[0].embedding içinde saklanır.
        response = self._client.generate_embedding(text.strip())
        vector: list[float] = response.data[0].embedding

        # İlk embedding'de boyutu kaydet (debug için yararlı)
        if self._embedding_dim is None:
            self._embedding_dim = len(vector)
            logger.debug(f"Embedding boyutu: {self._embedding_dim}")

        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Birden fazla metni sırayla embed eder ve vektör listesi döner.

        Args:
            texts: Embed edilecek metin listesi

        Returns:
            Her metne karşılık gelen embedding vektörleri listesi
        """
        return [self.embed(text) for text in texts]

    @property
    def embedding_dim(self) -> Optional[int]:
        """İlk embedding sonrası öğrenilen vektör boyutu."""
        return self._embedding_dim

    @property
    def is_loaded(self) -> bool:
        """Model yüklenmiş mi?"""
        return self._is_loaded


# Uygulama genelinde tek bir embedder instance'ı kullanılır
# (Generator modülü de aynı Foundry Local manager'ı kullanacak)
_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """
    Global embedder instance'ını döner.
    Yoksa oluşturur ama yüklemez — load() ayrıca çağrılmalı.
    """
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
