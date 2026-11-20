import os
import json
import socket
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import requests
from cachetools import TTLCache, cached
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

IPINFO_TOKEN = os.getenv("IPINFO_TOKEN")
ABUSEIPDB_KEY = os.getenv("ABUSEIPDB_KEY")
API_TOKEN = os.getenv("API_TOKEN")

USER_AGENT = "my-ip-lookup/1.0"
HEADERS = {"User-Agent": USER_AGENT}

app = FastAPI(title="IP Lookup API", version="1.0")

cache = TTLCache(maxsize=1000, ttl=600)

def safe_get(d: Optional[Dict[str, Any]], *keys):
    if not d:
        return None
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur

def reverse_dns(ip: str) -> Optional[str]:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None
    
def get_contact_from_rdap(rdap_data: Dict[str, Any], role_name: str, field_name: str) -> Optional[str]:
    entities = rdap_data.get("entities", [])
    for entity in entities:
        if role_name in entity.get("roles", []):
            vcard_array = entity.get("vcardArray", [])
            
            if vcard_array and len(vcard_array) > 1 and isinstance(vcard_array[1], list):
                vcard_properties = vcard_array[1]
                
                for item in vcard_properties:
                    if isinstance(item, list) and len(item) > 3 and item[0] == field_name:
                        return item[3]

    return None

def query_ipinfo(ip: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://ipinfo.io/{ip}/json"
        headers = HEADERS.copy()
        if IPINFO_TOKEN:
            headers["Authorization"] = f"Bearer {IPINFO_TOKEN}"
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def query_ipapi_co(ip: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://ipapi.co/{ip}/json/"
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def query_ip_api(ip: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://demo.ip-api.com/json/{ip}"
        
        params = {
            "fields": "66842623",
            "lang": "en"
        }
        
        custom_headers = {
          "Host": "demo.ip-api.com",
          "Connection": "keep-alive",
          "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 4 Build/RD2A.211001.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.120 Mobile Safari/537.36",
          "Accept": "*/*",
          "Origin": "https://ip-api.com",
          "X-Requested-With": "mark.via.gp",
          "Sec-Fetch-Site": "same-site",
          "Sec-Fetch-Mode": "cors",
          "Sec-Fetch-Dest": "empty",
          "Referer": "https://ip-api.com/",
          "Accept-Encoding": "gzip, deflate",
          "Accept-Language": "en-US,en;q=0.9"
        }
        
        r = requests.get(url, headers=custom_headers, params=params, timeout=6)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                return data
    except Exception:
        pass
    return None

def query_abuseipdb(ip: str) -> Optional[Dict[str, Any]]:
    if not ABUSEIPDB_KEY:
        return None
    try:
        url = "https://api.abuseipdb.com/api/v2/check"
        headers = {"Key": ABUSEIPDB_KEY, "Accept": "application/json"}
        params = {"ipAddress": ip}
        r = requests.get(url, headers=headers, params=params, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def query_rdap_apnic(ip: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://rdap.apnic.net/ip/{ip}"
        
        custom_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 4 Build/RD2A.211001.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.120 Mobile Safari/537.36",
            "Accept": "application/rdap+json",
            "Origin": "https://browserleaks.com",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "x-requested-with": "mark.via.gp",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        r = requests.get(url, headers=custom_headers, timeout=8)
        
        print(f"--- RDAP Debug: {ip} ---")
        print(f"Status Code: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print("RDAP Call Succeeded. Data found.")
            return data
        elif r.status_code == 404:
            print("RDAP Call Succeeded. IP not found in APNIC.")
            return {} 
        else:
             print(f"RDAP Call Failed. Response text: {r.text[:100]}...")
    except Exception as e:
        print(f"RDAP Call Failed with Exception: {e}")
    return None


def query_ipwho(ip: str) -> Optional[Dict[str, Any]]:
    # --- fonte sem chave: geolocalização em PT-BR, conexão, moeda e bandeira. ---
    try:
        r = requests.get(f"https://ipwho.is/{ip}", params={"lang": "pt-BR"},
                         headers=HEADERS, timeout=8)
        if r.status_code == 200:
            dados = r.json() or {}
            if dados.get("success") is True:
                return dados
    except Exception:
        pass
    return None


def query_ip2location(ip: str) -> Optional[Dict[str, Any]]:
    # --- modo keyless: 1.000 consultas/dia, fonte independente. ---
    try:
        r = requests.get("https://api.ip2location.io/", params={"ip": ip},
                         headers=HEADERS, timeout=8)
        if r.status_code == 200:
            dados = r.json() or {}
            if not dados.get("error") and dados.get("ip"):
                return dados
    except Exception:
        pass
    return None


def query_rdap_global(ip: str) -> Optional[Dict[str, Any]]:
    # --- agregador RDAP: consulta automaticamente o registry correto. ---
    try:
        r = requests.get(f"https://rdap.org/ip/{ip}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return {}
    except Exception:
        pass
    return None


def _rdap_entidades(rdap: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Lista todas as entidades RDAP com papéis e contatos."""
    if not isinstance(rdap, dict):
        return []
    saida = []
    for entidade in rdap.get("entities", []):
        contatos = []
        vcard = entidade.get("vcardArray", [])
        if len(vcard) > 1 and isinstance(vcard[1], list):
            for item in vcard[1]:
                if isinstance(item, list) and len(item) >= 4:
                    contatos.append({"tipo": item[0], "valor": item[3]})
        saida.append({
            "handle": entidade.get("handle"),
            "roles": entidade.get("roles", []),
            "contatos": contatos,
            "eventos": entidade.get("events", []),
        })
    return saida


def build_result(ip: str, srcs: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    """Normaliza e devolve o máximo de campos de todas as fontes consultadas."""
    def pick(*keys):
        for s in srcs.values():
            if not s:
                continue
            for k in keys:
                if k in s and s[k] not in (None, "", 0, False):
                    return s[k]
        return None

    rdap = srcs.get("rdap_global") or srcs.get("rdap_apnic") or {}
    ipinfo = srcs.get("ipinfo") or {}
    ipapi = srcs.get("ipapi") or {}
    ipapi_co = srcs.get("ip-api") or {}
    ipwho = srcs.get("ipwho") or {}
    ip2loc = srcs.get("ip2location") or {}
    abuse = safe_get(srcs.get("abuseipdb") or {}, "data") or {}

    lat = pick("latitude", "lat")
    lon = pick("longitude", "lon")
    loc = f"{lat},{lon}" if lat and lon else ""

    as_field = pick("as") or ""
    asn_num, asn_name = "", ""
    if isinstance(as_field, str):
        partes = as_field.split(" ", 1)
        if partes and partes[0].upper().startswith("AS"):
            asn_num = partes[0]
            asn_name = partes[1] if len(partes) > 1 else ""
        else:
            asn_name = as_field
    asn_num = pick("asn") or asn_num
    asn_name = pick("asname") or asn_name

    company = safe_get(ipinfo, "company") or {}
    organizacao = {
        "nome": pick("isp", "org") or safe_get(rdap, "name") or "",
        "isp": pick("isp") or "",
        "dominio": company.get("domain") or abuse.get("domain") or "",
        "tipo": company.get("type") or "",
        "asn": asn_num,
        "asn_nome": asn_name,
        "as_string": as_field,
        "bloco_rdap": safe_get(rdap, "handle") or "",
        "pais_rdap": safe_get(rdap, "country") or "",
        "nome_rdap": safe_get(rdap, "name") or "",
    }

    privacidade = {}
    for origem in (ipinfo, ipapi, ipapi_co):
        p = origem.get("privacy")
        if isinstance(p, dict):
            for chave, valor in p.items():
                if valor is True:
                    privacidade[chave] = True
    for chave in ("mobile", "proxy", "hosting"):
        if pick(chave):
            privacidade[chave] = True
    seguranca = {
        "is_mobile": bool(pick("mobile")),
        "is_vpn": bool(privacidade.get("vpn")),
        "is_proxy": bool(pick("proxy") or privacidade.get("proxy")),
        "is_tor": bool(privacidade.get("tor")),
        "is_relay": bool(privacidade.get("relay")),
        "is_hosting": bool(pick("hosting") or privacidade.get("hosting")),
        "abuse_score": safe_get(srcs.get("abuseipdb") or {}, "data", "abuseConfidenceScore") or 0,
        "abuse_total_reports": abuse.get("totalReports"),
        "abuse_last_reported": abuse.get("lastReportedAt"),
        "abuse_usage_type": abuse.get("usageType"),
        "abuse_domain": abuse.get("domain"),
        "abuse_isp": abuse.get("isp"),
        "abuse_categories": abuse.get("categories", []),
    }

    contatos = {
        "abuse_email": get_contact_from_rdap(rdap, "abuse", "email") or "",
        "tech_email": get_contact_from_rdap(rdap, "technical", "email") or "",
        "abuse_phone": get_contact_from_rdap(rdap, "abuse", "tel")
        or get_contact_from_rdap(rdap, "registrant", "tel") or "",
        "entidades": _rdap_entidades(rdap),
    }

    return {
        "ip": ip,
        "hostname": pick("reverse", "hostname") or reverse_dns(ip) or "",
        "consultado_em": int(time.time()),
        "localizacao": {
            "cidade": pick("city") or "",
            "regiao": pick("region", "regionName") or "",
            "codigo_regiao": pick("regionCode") or "",
            "pais": pick("country") or "",
            "codigo_pais": pick("countryCode", "country") or "",
            "continente": pick("continent") or "",
            "codigo_continente": pick("continentCode") or "",
            "latitude": lat,
            "longitude": lon,
            "loc": loc,
            "fuso": pick("timezone") or "",
            "offset": pick("offset") or "",
            "cep": pick("postal", "zip") or "",
            "codigo_telefone": pick("country_calling_code", "callingCode") or "",
            "bandeira": pick("countryFlag", "flag") or "",
            "moeda": pick("currency") or "",
            "idiomas": pick("languages") or "",
            "e_uniao_europeia": pick("is_eu"),
        },
        "rede": {
            "isp": pick("isp") or "",
            "organizacao": pick("org") or "",
            "asn": asn_num,
            "asn_nome": asn_name,
            "as_string": as_field,
            "dominio": company.get("domain") or abuse.get("domain") or "",
            "bloco": safe_get(rdap, "handle") or "",
            "reverso": pick("reverse") or "",
            "consulta": pick("query") or ip,
            "status": pick("status") or "",
            "mensagem": pick("message") or "",
        },
        "organizacao": organizacao,
        "seguranca": seguranca,
        "contatos": contatos,
        "rdap": {
            "handle": rdap.get("handle"),
            "nome": rdap.get("name"),
            "tipo": rdap.get("type"),
            "inicio": rdap.get("startAddress"),
            "fim": rdap.get("endAddress"),
            "pais": rdap.get("country"),
            "eventos": rdap.get("events", []),
            "observacoes": rdap.get("remarks", []),
            "links": rdap.get("links", []),
            "entidades": contatos["entidades"],
        },
        "extras": {
            "tipo_ip": ipwho.get("type") or "",
            "continente_codigo": ipwho.get("continent_code") or pick("continentCode") or "",
            "codigo_regiao": ipwho.get("region_code") or pick("regionCode") or "",
            "bandeira_emoji": safe_get(ipwho, "flag", "emoji") or "",
            "bandeira_img": safe_get(ipwho, "flag", "img") or "",
            "moeda": ipwho.get("currency") or {},
            "fuso_atual": safe_get(ipwho, "timezone", "current_time") or "",
            "fuso_id": ipwho.get("timezone") or pick("timezone") or "",
            "conexao": ipwho.get("connection") or {},
            "seguranca_ipwho": ipwho.get("security") or {},
            "ip2location": {
                "asn": ip2loc.get("asn") or "",
                "as": ip2loc.get("as") or "",
                "is_proxy": ip2loc.get("is_proxy"),
                "time_zone": ip2loc.get("time_zone") or "",
                "zip_code": ip2loc.get("zip_code") or "",
                "mensagem": ip2loc.get("message") or "",
            },
        },
        "fontes": {
            nome: {
                "disponivel": dados is not None,
                "vazio": dados == {},
                "dados": dados,
            }
            for nome, dados in srcs.items()
        },
    }


@cached(cache)
def lookup_ip(ip: str) -> Dict[str, Any]:
    sources = {
        "ipinfo": query_ipinfo(ip),
        "ipapi": query_ipapi_co(ip),
        "ip-api": query_ip_api(ip),
        "ipwho": query_ipwho(ip),
        "ip2location": query_ip2location(ip),
        "abuseipdb": query_abuseipdb(ip),
        "rdap_apnic": query_rdap_apnic(ip),
        "rdap_global": query_rdap_global(ip),
    }
    
    print(f"\n--- Final Merge Check for {ip} ---")
    if sources["rdap_apnic"] is None:
        print("RDAP source is NONE (Query failed or exception occurred).")
    elif sources["rdap_apnic"] == {}:
        print("RDAP source is empty dict (404/Not Found).")
    else:
        print("RDAP source contains data.")
        
    return build_result(ip, sources)


def check_auth(request: Request):
    if API_TOKEN is None:
        return True
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth.split(" ", 1)[1].strip()
    return token == API_TOKEN


@app.get("/ping")
async def ping():
    return {"ok": True, "service": "ip-lookup"}


@app.get("/lookup")
async def lookup(request: Request, ip: str = Query(..., description="Target IP address")):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="unauthorized")

    try:
        result = lookup_ip(ip)
        return JSONResponse(content=result)
    except Exception as e:
        print(f"An error occurred during lookup: {e}") 
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# --- o mesmo serviço serve o site estático em /. As rotas /ping e /lookup vêm antes. --- #
PUBLICO = Path(__file__).resolve().parent / "public"
if PUBLICO.exists():
    app.mount("/", StaticFiles(directory=str(PUBLICO), html=True), name="site")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
