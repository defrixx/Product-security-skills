import { unstable_cache } from 'next/cache';
import { randomUUID } from 'node:crypto';

// Synthetic identities and revocation store only. Never deploy this fixture.
const identities: Record<string, string> = { 'Bearer SYNTHETIC_ALICE': 'alice', 'Bearer SYNTHETIC_BOB': 'bob' };
const revoked = new Set<string>();
const readProfile = unstable_cache(async (actor: string, variant: string) => ({
  owner: actor, variant, value: `private-${actor}-${variant}`, computation: randomUUID()
}), ['synthetic-profile-v1'], { revalidate: 3600 });
// Deliberately unsafe: the authenticated first result is reused without actor separation.
const readUnsafe = unstable_cache(async () => ({ owner: 'alice', value: 'private-alice', computation: randomUUID() }), ['synthetic-unsafe-profile'], { revalidate: 3600 });

export async function GET(request: Request) {
  const actor = identities[request.headers.get('authorization') || ''];
  const query = new URL(request.url).searchParams;
  if (query.get('unsafe') === '1') return Response.json(await readUnsafe());
  if (!actor) return new Response('Unauthorized', { status: 401 });
  if (revoked.has(actor)) return new Response('Revoked', { status: 403 });
  const variant = query.get('variant') || 'short';
  if (!['short', 'full'].includes(variant)) return new Response('Invalid', { status: 400 });
  // Current authorization runs on every request, outside cached computation.
  return Response.json(await readProfile(actor, variant), { headers: { 'Cache-Control': 'private, no-store' } });
}
export async function POST(request: Request) {
  const actor = identities[request.headers.get('authorization') || ''];
  if (!actor) return new Response('Unauthorized', { status: 401 });
  revoked.add(actor);
  return Response.json({ revoked: true });
}
