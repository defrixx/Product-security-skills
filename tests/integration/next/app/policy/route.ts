// Synthetic browser policy endpoints. Unsafe/report-only controls are intentional.
export async function GET(request: Request) {
  const query = new URL(request.url).searchParams;
  const mode = query.get('mode') || 'enforce';
  const headers: Record<string, string> = { 'Content-Type': 'text/html', 'Cache-Control': 'no-store' };
  const csp = "default-src 'none'; script-src 'nonce-synthetic'; frame-ancestors 'self'";
  if (mode === 'enforce') headers['Content-Security-Policy'] = csp;
  if (mode === 'report') headers['Content-Security-Policy-Report-Only'] = csp;
  return new Response(`<p id="ready">synthetic document</p>
<script nonce="synthetic">window.allowed=true;parent.postMessage('synthetic-frame-ready','*')</script>
<script>window.untrusted=true</script>`, { headers });
}
