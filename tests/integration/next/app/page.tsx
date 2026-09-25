import View from './view';
export const dynamic = 'force-dynamic';
export default function Page() {
  // Reading a private server variable is intentional; only a public boolean crosses the boundary.
  const configured = Boolean(process.env.SYNTHETIC_PRIVATE_CREDENTIAL);
  return <View configured={configured} />;
}
