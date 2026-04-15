import requests
import json
import time
import pandas as pd
from typing import Dict, List, Optional
from src.cache import cache_it

class SECEdgarClient:
    """
    Cliente para a API oficial da SEC (EDGAR).
    Referência: https://www.sec.gov/edgar/sec-api-documentation
    """
    BASE_DATA_URL = "https://data.sec.gov/api/xbrl/companyfacts/"
    TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
    
    # Header obrigatório pela SEC (Nome + Email)
    HEADERS = {
        "User-Agent": "InvestidorIA/2.0 david@investidor-ia.com",
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov"
    }

    @cache_it
    def _get_cik_mapping(self) -> Dict[str, str]:
        """Busca o mapeamento atualizado de Tickers para CIKs."""
        try:
            # SEC requer User-Agent específico até para o JSON de tickers
            headers = {"User-Agent": "InvestidorIA/2.0 david@investidor-ia.com"}
            resp = requests.get(self.TICKER_CIK_URL, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            mapping = {}
            for item in data.values():
                ticker = str(item['ticker']).upper()
                cik = str(item['cik_str']).zfill(10)
                mapping[ticker] = cik
            return mapping
        except Exception as e:
            print(f"[SEC Edgar] Erro ao buscar mapeamento CIK: {e}")
            return {}

    def get_cik(self, ticker: str) -> Optional[str]:
        mapping = self._get_cik_mapping()
        return mapping.get(ticker.upper())

    @cache_it
    def get_submissions(self, cik: str) -> Dict:
        """Busca a lista de submissões (filings) recentes da empresa."""
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[SEC Edgar] Erro ao buscar submissões para CIK {cik}: {e}")
            return {}

    @cache_it
    def get_company_facts(self, cik: str) -> Dict:
        """Busca todos os 'facts' (DRE, Balanço, etc) processados pela SEC."""
        url = f"{self.BASE_DATA_URL}CIK{cik}.json"
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[SEC Edgar] Erro ao buscar facts para CIK {cik}: {e}")
            return {}

    def extract_metric(self, facts: Dict, tag: str, taxonomy: str = "us-gaap") -> List[Dict]:
        """Extrai uma métrica específica do JSON da SEC."""
        try:
            units = facts.get('facts', {}).get(taxonomy, {}).get(tag, {}).get('units', {}).get('USD', [])
            if not units:
                # Tenta outras taxonomias ou unidades se necessário (ex: dei)
                units = facts.get('facts', {}).get('dei', {}).get(tag, {}).get('units', {}).get('USD', [])
            
            if not units: return []
            
            # Normaliza para lista de dicts
            result = []
            for entry in units:
                result.append({
                    'data': entry.get('end'),
                    'valor': entry.get('val'),
                    'form': entry.get('form'), # 10-K (Anual) ou 10-Q (Trimestral)
                    'fy': entry.get('fy'),
                    'fp': entry.get('fp')
                })
            return result
        except:
            return []

    def get_financials(self, ticker: str) -> Dict[str, List[Dict]]:
        """Consolida DRE, Balanço e Fluxo de Caixa a partir do EDGAR."""
        cik = self.get_cik(ticker)
        if not cik:
            return {}
            
        facts = self.get_company_facts(cik)
        if not facts:
            return {}

        # Mapeamento de Tags XBRL (us-gaap)
        # Notas: 'Revenues' pode variar por setor, mas us-gaap:Revenues é comum.
        metrics = {
            'receita_liquida': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet'],
            'lucro_liquido': ['NetIncomeLoss'],
            'ebit': ['OperatingIncomeLoss'],
            'ativo_total': ['Assets'],
            'patrimonio_liquido': ['StockholdersEquity'],
            'caixa': ['CashAndCashEquivalentsAtCarryingValue'],
            'divida': ['LongTermDebt', 'ShortTermBorrowings'],
            'fco': ['NetCashProvidedByUsedInOperatingActivities'],
            'fci': ['NetCashProvidedByUsedInInvestingActivities'],
            'fcf_raw': ['NetCashProvidedByUsedInFinancingActivities'],
            'capex': ['PaymentsToAcquirePropertyPlantAndEquipment']
        }

        extracted = {}
        for key, tags in metrics.items():
            data = []
            for tag in tags:
                data = self.extract_metric(facts, tag)
                if data: break
            extracted[key] = data

        return extracted

# Singleton para uso global
sec_client = SECEdgarClient()
