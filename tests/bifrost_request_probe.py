"""Trusted test probe; never deployed as an HTTP endpoint."""
import base64,http.client,json,socket,sys
try:
 data=json.load(sys.stdin)
 c=http.client.HTTPConnection(sys.argv[1],int(sys.argv[2]),timeout=4)
 c.request(data.get('method','GET'),data.get('path','/health'),body=data.get('body'),headers=data.get('headers',{}));r=c.getresponse();raw=r.read(1048577);c.close()
 print(json.dumps({'status':r.status,'body':base64.b64encode(raw).decode()}))
except Exception as e:print(json.dumps({'transport':'blocked','exception':type(e).__name__}))
