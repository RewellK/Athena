import re
import unicodedata

from sources.source_registry import SourceProposal


class SourceDiscoveryEngine:
    """Suggests source candidates. It does not validate or enable them."""

    CANDIDATES = {
        "weather": {
            "name": "Open-Meteo",
            "source_type": "api",
            "url": "https://open-meteo.com/",
            "reason": "Possível fonte de clima com API pública; ainda precisa validação local antes de uso.",
            "requires_api_key": "no",
            "supports_api": "yes",
            "connector_type": "weather_open_meteo",
            "freshness_ttl_seconds": 1800,
        },
        "news": {
            "name": "GDELT",
            "source_type": "api",
            "url": "https://www.gdeltproject.org/",
            "reason": "Possível fonte para descoberta de notícias; exige validação de conector e critérios editoriais.",
            "requires_api_key": "unknown",
            "supports_api": "unknown",
            "connector_type": "news_gdelt_stub",
            "freshness_ttl_seconds": 900,
        },
        "vehicles": {
            "name": "iCarros",
            "source_type": "website",
            "url": "https://www.icarros.com.br/",
            "reason": "Possível fonte para informações de veículos; precisa validar se permite consulta automatizada segura.",
            "requires_api_key": "unknown",
            "supports_api": "unknown",
            "connector_type": "generic_website_stub",
            "freshness_ttl_seconds": 86400,
        },
        "finance": {
            "name": "Banco Central do Brasil",
            "source_type": "api",
            "url": "https://www.bcb.gov.br/",
            "reason": "Possível fonte oficial para alguns dados financeiros; escopo e API precisam validação.",
            "requires_api_key": "unknown",
            "supports_api": "unknown",
            "connector_type": "finance_bcb_stub",
            "freshness_ttl_seconds": 900,
        },
        "sports": {
            "name": "Fonte esportiva configurável",
            "source_type": "custom_user_source",
            "url": "",
            "reason": "Domínio esportivo precisa de fonte escolhida e validada pelo usuário.",
            "requires_api_key": "unknown",
            "supports_api": "unknown",
            "connector_type": "custom_source_stub",
            "freshness_ttl_seconds": 900,
        },
        "places": {
            "name": "Fonte de lugares configurável",
            "source_type": "custom_user_source",
            "url": "",
            "reason": "Domínio de lugares precisa de fonte escolhida e validada pelo usuário.",
            "requires_api_key": "unknown",
            "supports_api": "unknown",
            "connector_type": "custom_source_stub",
            "freshness_ttl_seconds": 86400,
        },
        "documentation": {
            "name": "Fonte de documentação configurável",
            "source_type": "custom_user_source",
            "url": "",
            "reason": "Documentação deve ser adicionada com origem explícita e escopo claro.",
            "requires_api_key": "unknown",
            "supports_api": "unknown",
            "connector_type": "documentation_stub",
            "freshness_ttl_seconds": 604800,
        },
        "legal": {
            "name": "Fonte jurídica configurável",
            "source_type": "custom_user_source",
            "url": "",
            "reason": "Pesquisa jurídica precisa de fonte confiável, jurisdição clara e evidência obrigatória.",
            "requires_api_key": "unknown",
            "supports_api": "unknown",
            "connector_type": "legal_research_stub",
            "freshness_ttl_seconds": 86400,
        },
        "general_web": {
            "name": "Fonte web configurável",
            "source_type": "custom_user_source",
            "url": "",
            "reason": "Pesquisa geral precisa de fonte concreta aprovada antes de gerar evidência.",
            "requires_api_key": "unknown",
            "supports_api": "unknown",
            "connector_type": "custom_source_stub",
            "freshness_ttl_seconds": 3600,
        },
    }

    def detect_domain(self, text):
        normalized = self._normalize(text)
        words = set(normalized.split())

        if words & {"clima", "tempo", "previsao", "chuva", "temperatura", "calor", "frio"}:
            return "weather"
        if words & {"noticia", "noticias", "manchete", "manchetes", "jornal"}:
            return "news"
        if words & {"fipe", "carro", "veiculo", "veiculos", "moto", "automovel", "caminhonete"}:
            return "vehicles"
        if (words & {"preco", "valor", "custa", "custaria", "cotacao"}) and self._has_year(normalized):
            return "vehicles"
        if words & {"bitcoin", "dolar", "euro", "acao", "acoes", "cotacao", "bolsa", "cripto"}:
            return "finance"
        if words & {"jurisprudencia", "juridico", "juridica"}:
            return "legal"
        if words & {"placar", "jogo", "partida", "campeonato", "time"}:
            return "sports"
        if words & {"restaurante", "endereco", "loja", "lugar", "perto", "local"}:
            return "places"
        if words & {"documentacao", "docs", "manual", "api"}:
            return "documentation"
        if words & {"hoje", "agora", "atual", "atuais", "recente", "recentes"}:
            return "general_web"
        return "unknown_external"

    def proposal_for(self, domain, query=""):
        domain = domain if domain in self.CANDIDATES else "general_web"
        data = dict(self.CANDIDATES[domain])
        return SourceProposal(
            domain=domain,
            name=data["name"],
            source_type=data.get("source_type", "website"),
            url=data.get("url", ""),
            reason=data.get("reason", ""),
            requires_api_key=data.get("requires_api_key", "unknown"),
            supports_api=data.get("supports_api", "unknown"),
            connector_type=data.get("connector_type", "generic_website_stub"),
            trust_level="unverified",
            freshness_ttl_seconds=int(data.get("freshness_ttl_seconds", 3600)),
            status="candidate",
            discovered_by="source_discovery",
            validation_status="not_validated",
            requires_human_approval=True,
        )

    def discover(self, query, domain=None):
        domain = domain or self.detect_domain(query)
        return self.proposal_for(domain, query=query)

    def _normalize(self, text):
        text = str(text or "").strip().lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    def _has_year(self, text):
        return bool(re.search(r"\b(19[8-9][0-9]|20[0-3][0-9])\b", text))
