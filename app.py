import os
import json
import socket
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


def build_result(ip: str, srcs: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    def pick(*keys):
        for s in srcs.values():
            if not s:
                continue
            for k in keys:
                if k in s and s[k] not in (None, "", 0): 
                    return s[k]
        return None

    lat = pick("latitude", "lat")
    lon = pick("longitude", "lon")
    loc = f"{lat},{lon}" if lat and lon else ""
    rdap_data = srcs.get("rdap_apnic")
    
    full_country_name = pick("country") or "" 
    country_code = pick("countryCode", "country") or ""
    if not full_country_name and country_code:
        full_country_name = country_code

    asn_num = ""
    asn_name = ""
    as_field = pick("as")
    if isinstance(as_field, str):
        parts = as_field.split(" ", 1)
        if parts and parts[0].upper().startswith("AS"):
            asn_num = parts[0]
            asn_name = parts[1] if len(parts) > 1 else "" 
        else:
            asn_name = as_field
    asn_name = pick("asname") or asn_name

    company_obj = {"name": "", "domain": "", "type": ""}
    
    rdap_org_name = safe_get(rdap_data, "name")
    company_obj["name"] = pick("isp", "org") or rdap_org_name or ""
    
    ipinfo_company = safe_get(srcs.get("ipinfo") or {}, "company")
    if isinstance(ipinfo_company, dict):
        company_obj["name"] = ipinfo_company.get("name") or company_obj["name"]
        company_obj["domain"] = ipinfo_company.get("domain") or ""
        company_obj["type"] = ipinfo_company.get("type") or ""

    privacy = {"mobile": False, "vpn": False, "proxy": False, "tor": False, "relay": False, "hosting": False}
    privacy["mobile"] = pick("mobile") or False 
    privacy["proxy"] = pick("proxy") or False
    privacy["hosting"] = pick("hosting") or False

    for sname in ("ipinfo", "ipapi"):
        s = srcs.get(sname)
        if not s:
            continue
        p = s.get("privacy")
        if isinstance(p, dict):
            for k in ("vpn", "proxy", "tor", "relay", "hosting"):
                if p.get(k) is True: 
                    privacy[k] = True
    
    abuse_score = safe_get(srcs.get("abuseipdb") or {}, "data", "abuseConfidenceScore") or 0
    
    whois_contacts = {
        "abuse_email": "",
        "tech_email": "",
        "abuse_phone": "",
    }
    
    if rdap_data:
        whois_contacts["abuse_email"] = get_contact_from_rdap(rdap_data, "abuse", "email")
        whois_contacts["tech_email"] = get_contact_from_rdap(rdap_data, "technical", "email")
        
        abuse_phone = get_contact_from_rdap(rdap_data, "abuse", "tel")
        if not abuse_phone:
             abuse_phone = get_contact_from_rdap(rdap_data, "registrant", "tel")
             
        whois_contacts["abuse_phone"] = abuse_phone
        
        print(f"RDAP Contacts Found: {whois_contacts}")


    return {
        "ip": ip,
        "hostname": pick("reverse", "hostname") or reverse_dns(ip) or "", 
        
        "location": {
            "city": pick("city") or "",
            "region": pick("region", "regionName") or "",
            "country": full_country_name, 
            "countryCode": country_code,
            "continent": pick("continent") or "",
            "loc": loc,
            "timezone": pick("timezone") or "",
        },
        
        "organization": {
            "name": company_obj["name"],
            "isp": pick("isp") or company_obj["name"],
            "asn": asn_num,
            "asn_name": asn_name,
            "ip_range": safe_get(rdap_data, "handle")
        },
        
        "security": {
            "is_mobile": privacy["mobile"],
            "is_vpn": privacy["vpn"],
            "is_proxy": privacy["proxy"],
            "is_hosting": privacy["hosting"],
            "abuse_score": abuse_score
        },
        
        "whois_contacts": whois_contacts
    }


@cached(cache)
def lookup_ip(ip: str) -> Dict[str, Any]:
    sources = {
        "ipinfo": query_ipinfo(ip),
        "ipapi": query_ipapi_co(ip),
        "ip-api": query_ip_api(ip),
        "abuseipdb": query_abuseipdb(ip),
        "rdap_apnic": query_rdap_apnic(ip)
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
