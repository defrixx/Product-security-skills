'use client';
import { useState } from 'react';
export default function View({ configured }: { configured: boolean }) {
  const [value, setValue] = useState('');
  return <main><p>Configured: {String(configured)}</p><input aria-label="Untrusted text" value={value} onChange={e => setValue(e.target.value)} /><div data-testid="rendered">{value}</div></main>;
}
