"""Isolated browser session with a single owner thread and bounded operations."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.parse
from .web import validate_url


class Browser:
    def __init__(self,settings):
        self.settings=settings
        self.worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='athena-browser')
        self.playwright=self.browser=self.page=None
        self.targets={}

    def validate(self,url):
        origin=urllib.parse.urlsplit(url)
        if origin.scheme not in {'https','http'} or origin.username or origin.password: raise ValueError('URL inválida')
        exact=urllib.parse.urlunsplit((origin.scheme,origin.netloc,'','',''))
        # Local fixture origins must be explicitly configured. Default is public HTTPS.
        if exact in self.settings.get('browserAllowedOrigins',[]): return
        validate_url(url)

    def start(self):
        if self.page is not None: return
        from playwright.sync_api import sync_playwright
        self.playwright=sync_playwright().start()
        chrome=Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        kwargs={'headless':True}
        if chrome.exists(): kwargs['executable_path']=str(chrome)
        self.browser=self.playwright.chromium.launch(**kwargs)
        self.page=self.browser.new_page(accept_downloads=False)
        self.page.set_default_timeout(12000)
        def gate(route):
            url=route.request.url
            if url.startswith(('data:','about:')): route.continue_();return
            try: self.validate(url)
            except Exception: route.abort();return
            route.continue_()
        self.page.route('**/*',gate)

    def snapshot(self):
        self.targets={}
        elements=[]
        handles=self.page.locator('a[href],button,input:not([type=hidden]),textarea,select')
        for i in range(min(handles.count(),50)):
            element=handles.nth(i)
            if not element.is_visible(): continue
            tag=element.evaluate('(e)=>e.tagName.toLowerCase()')
            label=(element.inner_text() or element.get_attribute('aria-label') or element.get_attribute('placeholder') or element.get_attribute('name') or '')[:100]
            target=str(len(elements)+1);self.targets[target]=element
            elements.append({'id':target,'tag':tag,'label':label,'href':element.get_attribute('href') if tag=='a' else None})
        return {'url':self.page.url,'title':self.page.title(),'content':self.page.inner_text('body')[:6000],
                'elements':elements,'source':'browser_untrusted'}

    def work(self,args):
        if not self.settings.get('allowExternalRequests',False): raise ValueError('Navegação desativada')
        self.start()
        operation=args['operation']
        if operation=='navigate':
            self.validate(args['url']);self.page.goto(args['url'],wait_until='domcontentloaded')
        elif operation in {'click','fill'}:
            target=self.targets.get(args.get('target'))
            if target is None: raise ValueError('Consulte a página e use um ID de elemento retornado')
            tag=target.evaluate('(e)=>e.tagName.toLowerCase()')
            if operation=='click' and tag=='a':
                destination=urllib.parse.urljoin(self.page.url,target.get_attribute('href') or '')
                self.validate(destination)
                self.page.goto(destination,wait_until='domcontentloaded')
            else:
                if not self.settings.get('browserInteractionEnabled',False):
                    raise ValueError('Preenchimento e botões exigem browserInteractionEnabled=true')
                if operation=='fill': target.fill(args['text'])
                else: target.click()
        elif operation!='inspect': raise ValueError('Operação de navegador inválida')
        return self.snapshot()

    def execute(self,args):
        return self.worker.submit(self.work,args).result(timeout=40)

    def close(self):
        def cleanup():
            if self.browser: self.browser.close()
            if self.playwright: self.playwright.stop()
            self.playwright=self.browser=self.page=None
        self.worker.submit(cleanup).result(timeout=10)
        self.worker.shutdown(wait=True,cancel_futures=True)
