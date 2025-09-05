from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any

class PaymentProcessor(ABC):
    """Classe de base abstraite pour tous les processeurs de paiement."""
    
    @abstractmethod
    def initialize_payment(self, amount: Decimal, order_id: str, **kwargs) -> Dict[str, Any]:
        """Initialise un paiement."""
        pass
    
    @abstractmethod
    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'un paiement."""
        pass
    
    @abstractmethod
    def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Traite les webhooks du processeur de paiement."""
        pass
