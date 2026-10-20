"""Public HTTPS document reading, bounded redirects/body and no ambient proxy."""
import html.parser
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request


class Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}: self.hidden+=1
    def handle_endtag(self,tag):
        if tag in {'script','style'}: self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden and data.strip(): self.parts.append(data.strip())


def validate_url(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443) or len(url)>2000:
        raise ValueError('Leitura web exige HTTPS público na porta 443, sem credenciais')
    addresses=socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise ValueError('Endereços locais ou privados não são permitidos na leitura web')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


def read_public(url, settings):
    if not settings.get('allowExternalRequests',False): raise ValueError('Consulta web desativada')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    for _ in range(4):
        validate_url(url)
        try:
            response=opener.open(urllib.request.Request(url,headers={'User-Agent':'Athena/1.0'}),timeout=12)
        except urllib.error.HTTPError as error:
            if error.code in {301,302,303,307,308} and error.headers.get('Location'):
                url=urllib.parse.urljoin(url,error.headers['Location']); error.close(); continue
            raise
        with response:
            content_type=response.headers.get_content_type()
            if content_type not in {'text/plain','text/html','application/json'}: raise ValueError('Formato web não suportado')
            body=response.read(256001)
        if len(body)>256000: raise ValueError('Página excede 256 KB')
        text=body.decode('utf-8',errors='replace')
        if content_type=='text/html':
            parser=Text();parser.feed(text);text=' '.join(parser.parts)
        return {'url':url,'content':text[:10000],'source':'external_untrusted','truncated':len(text)>10000}
    raise ValueError('Redirecionamentos demais')


def search_public(query,settings):
    if not settings.get('allowExternalRequests',False): raise ValueError('Busca externa desativada')
    if not isinstance(query,str) or not 1<=len(query)<=500: raise ValueError('Consulta de 1 a 500 caracteres')
    from ddgs import DDGS
    results=DDGS(timeout=8,verify=True).text(query,max_results=5,backend='duckduckgo')
    items=[]
    for item in results[:5]:
        url=item.get('href','');parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:continue
        items.append({'title':str(item.get('title',''))[:180],'url':url[:2000],'snippet':str(item.get('body',''))[:500]})
    if not items: raise ValueError('A busca não retornou fontes utilizáveis; não vou inventar resultados')
    return {'results':items,'source':'duckduckgo_untrusted','api_key_required':False}
