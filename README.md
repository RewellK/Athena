# Athena V12.4 — LLM-Guided Intent & Target Resolution

Athena é uma entidade digital persistente em evolução.

Princípio central:

```text
Athena usa LLMs.
LLMs não são Athena.
```

## O que mudou na V12.4

A V12.4 corrige a interpretação conversacional.

A Athena não deve entender linguagem por listas de palavras ou frases. Agora a entrada do usuário passa primeiro por:

```text
IntentResolutionEngine
↓
LLM
↓
JSON estrutural
↓
Athena Core
```

O Athena Core continua sendo responsável por:

- validar intenção;
- consultar memória;
- consultar World Model;
- consultar Self Model;
- verificar ferramentas disponíveis;
- decidir se aprende;
- responder sem inventar informação externa.

## Como iniciar no terminal

```bash
python main.py
```

## Como iniciar a interface desktop

Instale dependências:

```bash
pip install -r requirements.txt
```

Execute:

```bash
python app.py
```

Se `customtkinter` não estiver instalado, a Athena informa a dependência ausente sem quebrar o núcleo.

## Configuração principal

Arquivo:

```text
config/settings.json
```

Configurações relevantes da V12.4:

```json
{
  "useLLM": true,
  "useLLMIntentResolution": true,
  "allowLocalIntentFallback": false,
  "useRegexFallback": false,
  "enableLegacyParsers": false
}
```

## Fluxo conversacional

Exemplos esperados:

```text
Usuário: Quem sou eu?
Athena: responde sobre Rewell, não sobre Athena.

Usuário: Quem é você?
Athena: responde identidade da Athena.

Usuário: Quem é Fernanda?
Athena: consulta World Model/memória.

Usuário: Como está o clima hoje?
Athena: verifica ferramenta. Se não houver ferramenta de clima, não inventa.
```

## Ferramentas externas

A V12.4 não implementa clima, notícias ou internet em tempo real.

Quando o usuário pede informação externa, Athena verifica o `ToolRegistry`. Se não existir ferramenta compatível, responde honestamente.

## Auditoria

Leia:

```text
AUDIT_V12_4.md
```

Ela lista regras removidas, rotas suportadas, limitações e riscos restantes.

## Testes manuais sugeridos

```text
Quem é você?
Quem sou eu?
Quem te criou?
Quem é Fernanda?
Fernanda é o amor da minha vida.
Quem é Fernanda?
Como está o clima hoje?
Como está o clima hoje em Embu das Artes?
Quais são as notícias de hoje?
Olá Athena, quem é você?
Bom dia, quem sou eu?
Oi Athena, quem é Fernanda?
```

Resultado esperado:

- sem invenção de clima/notícias;
- sem confundir usuário com Athena;
- sem transformar toda frase em entidade;
- sem regex cognitivo;
- sem regras locais por frase;
- decisões baseadas em JSON estrutural da LLM.
