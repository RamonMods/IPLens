# IPLens

Consulta de IP em uma tela: localização, operadora, ASN, sinais de VPN/proxy e contatos de abuso. Site e API no mesmo serviço FastAPI.

- Site: https://ramonmods.github.io/IPLens/

## Como usar

Digite um IPv4 ou IPv6 e clique em **consultar**. Também dá para clicar nos exemplos (`8.8.8.8`, `1.1.1.1`). A resposta junta dados de oito fontes e mostra quatro cards: localização, rede, segurança e contatos. Abaixo existe o JSON completo da resposta.

## API

```
GET /lookup?ip=8.8.8.8
GET /ping
```

`/lookup` aceita `Authorization: Bearer TOKEN` quando `API_TOKEN` está definido. Sem essa variável, a rota é aberta. Resposta em JSON:

```json
{
  "ip": "8.8.8.8",
  "hostname": "dns.google",
  "consultado_em": 1795000000,
  "localizacao": {
    "cidade": "Mountain View", "regiao": "California", "pais": "US",
    "continente": "North America", "latitude": 37.4223, "longitude": -122.0850,
    "fuso": "America/Los_Angeles", "cep": "94043", "moeda": "USD"
  },
  "rede": {
    "isp": "Google LLC", "organizacao": "Google LLC", "asn": "AS15169",
    "asn_nome": "GOOGLE", "dominio": "google.com", "bloco": "NET-8.8.8.0-8"
  },
  "organizacao": { "nome": "Google LLC", "tipo": "Content Delivery Network" },
  "seguranca": {
    "is_mobile": false, "is_vpn": false, "is_proxy": false,
    "is_tor": false, "is_relay": false, "is_hosting": false, "abuse_score": 0
  },
  "contatos": { "abuse_email": "", "tech_email": "", "entidades": [] },
  "rdap": { "handle": "NET-8.8.8.0-8", "eventos": [], "links": [] },
  "fontes": {
    "ipinfo": { "disponivel": true, "vazio": false, "dados": {} },
    "ipapi": { "disponivel": true, "vazio": false, "dados": {} },
    "ip-api": { "disponivel": true, "vazio": false, "dados": {} },
    "abuseipdb": { "disponivel": false, "vazio": false, "dados": null },
    "rdap_apnic": { "disponivel": true, "vazio": false, "dados": {} }
  }
}
```

Fontes consultadas: IPinfo, ipapi.co, ip-api.com, IPWho.is, IP2Location (keyless), AbuseIPDB, RDAP/APNIC e RDAP global (rdap.org). Cache de 10 minutos por IP.

## Rodando local

```bash
pip install -r requirements.txt
python app.py
```

Abre em `http://127.0.0.1:5000`. O próprio FastAPI serve o site em `/`.

Variáveis de ambiente (opcionais, via `.env`):

| Variável | Para quê |
|---|---|
| `IPINFO_TOKEN` | aumenta cota do IPinfo |
| `ABUSEIPDB_KEY` | habilita a pontuação de abuso |
| `API_TOKEN` | exige Bearer token em `/lookup` |

## Estrutura

```
app.py       FastAPI: /lookup, /ping e o site estático
public/      site (HTML, CSS, JS, fontes e ícones)
requirements.txt
vercel.json
```

O espelho no GitHub Pages é só a casca visual; sem a API publicada, a busca mostra aviso de indisponibilidade.

---

Se o IPLens te ajudou, um café ajuda a manter as consultas no ar: **[pixgg.com/ramon](https://pixgg.com/ramon)**
