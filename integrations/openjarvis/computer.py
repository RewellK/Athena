"""Fixed macOS operations. Model text is data, never an AppleScript program."""
from datetime import datetime
import subprocess
import sys
import time
import urllib.parse

CALENDAR_LIST = '''on run argv
 tell application "Calendar"
  set output to ""
  repeat with c in calendars
   set output to output & name of c & linefeed
  end repeat
  return output
 end tell
end run'''
CALENDAR_CREATE = '''on run argv
 set startDate to (current date) + ((item 4 of argv as real) - (item 6 of argv as real))
 set endDate to (current date) + ((item 5 of argv as real) - (item 6 of argv as real))
 tell application "Calendar"
  set targetCalendar to first calendar whose name is (item 1 of argv)
  tell targetCalendar
   set e to make new event with properties {summary:(item 2 of argv), description:(item 3 of argv), start date:startDate, end date:endDate}
   return uid of e
  end tell
 end tell
end run'''


class Computer:
    APPS={'calculator':'Calculator','calendar':'Calendar','notes':'Notes','textedit':'TextEdit','safari':'Safari','reminders':'Reminders'}

    def __init__(self,settings):
        self.settings=settings

    def enabled(self):
        if sys.platform!='darwin': raise ValueError('Esta ferramenta exige macOS')
        if not self.settings.get('computerToolsEnabled',False): raise ValueError('Ferramentas de aplicativos desativadas')

    def app(self,args):
        self.enabled()
        name=args['name'].casefold()
        if name not in self.APPS: raise ValueError('Aplicativo não permitido. Opções: '+', '.join(self.APPS))
        subprocess.run(['/usr/bin/open','-a',self.APPS[name]],check=True,timeout=10,capture_output=True)
        return {'application':self.APPS[name],'status':'open_requested','verified':'macOS accepted request; window content not inspected'}

    def browser(self,args):
        self.enabled()
        url=args['url']; parsed=urllib.parse.urlsplit(url)
        if parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password or len(url)>2000:
            raise ValueError('Use URL HTTP/HTTPS sem credenciais')
        subprocess.run(['/usr/bin/open',url],check=True,timeout=10,capture_output=True)
        return {'url':url,'status':'open_requested','verified':'macOS accepted request; page rendering not inspected'}

    def calendar(self,args):
        self.enabled()
        operation=args['operation']
        if operation=='list':
            result=subprocess.run(['/usr/bin/osascript','-e',CALENDAR_LIST],check=True,timeout=15,capture_output=True,text=True)
            return {'calendars':result.stdout.strip().splitlines()[:100]}
        required={'calendar','title','start','end'}
        if not required<=set(args): raise ValueError('Criar evento exige calendar, title, start e end com fuso')
        start,end=(datetime.fromisoformat(args[x]) for x in ('start','end'))
        if not start.tzinfo or not end.tzinfo or not time.time()-60<=start.timestamp()<end.timestamp()<=time.time()+366*86400:
            raise ValueError('Datas com fuso, início anterior ao fim, dentro de um ano')
        result=subprocess.run(['/usr/bin/osascript','-e',CALENDAR_CREATE,args['calendar'],args['title'],args.get('description',''),
                               str(start.timestamp()),str(end.timestamp()),str(time.time())],check=True,timeout=15,capture_output=True,text=True)
        uid=result.stdout.strip()
        if not uid: raise RuntimeError('Calendar não retornou identificador')
        return {'calendar':args['calendar'],'title':args['title'],'event_uid':uid,'status':'created'}
