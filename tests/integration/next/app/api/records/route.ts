// Synthetic identity fixture only: fixed bearer tokens are NOT a production authentication pattern.
const identities: Record<string, string> = {
  'Bearer SYNTHETIC_ALICE': 'alice', 'Bearer SYNTHETIC_BOB': 'bob'
};
const record = { id: 'record-a', owner: 'alice', value: 'initial' };
export async function GET() { return Response.json({ value: record.value }); }
export async function POST(request: Request) {
  const identity = identities[request.headers.get('authorization') || ''];
  if (!identity) return Response.json({ error: 'Unauthorized' }, { status: 401 });
  let body;
  try { body = await request.json(); } catch { return Response.json({ error: 'Invalid' }, { status: 400 }); }
  if (!body || typeof body !== 'object' || Array.isArray(body) ||
      Object.keys(body).sort().join(',') !== 'id,value' || typeof body.id !== 'string' ||
      typeof body.value !== 'string' || !body.value.length || body.value.length > 32)
    return Response.json({ error: 'Invalid' }, { status: 400 });
  if (body.id !== record.id || record.owner !== identity)
    return Response.json({ error: 'Forbidden' }, { status: 403 });
  record.value = body.value;
  return Response.json({ saved: true });
}
