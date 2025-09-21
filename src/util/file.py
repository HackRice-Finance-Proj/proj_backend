import json
import os
from typing import Dict, Any
from fastapi import HTTPException

class DataLoader:
    """Utility class for loading static data files"""
    
    @staticmethod
    def load_credit_cards_data(file_path: str = 'credit_cards.json') -> Dict[str, Any]:
        """Load credit card data from JSON file"""
        try:
            # Load from file
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Credit cards data file not found: {file_path}")
            
            with open(file_path, 'r') as file:
                cards_data = json.load(file)
            
            print("✅ Credit cards data loaded successfully")
            return cards_data
            
        except FileNotFoundError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load credit cards data: {e}")