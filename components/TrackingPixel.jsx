'use client';

import { usePathname } from 'next/navigation';
import { useEffect } from 'react';

export function TrackingPixel() {
  const pathname = usePathname();

  useEffect(() => {
    // Fire tracking on pathname change
    // Replace with your actual tracking endpoint
    fetch('/api/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pathname, timestamp: Date.now() }),
    }).catch(console.error);
  }, [pathname]);

  return null;
}