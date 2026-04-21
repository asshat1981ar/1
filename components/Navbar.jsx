import Link from 'next/link';
import { ThemeToggle } from './ThemeToggle';

export function Navbar() {
  return (
    <nav className="w-full px-4 py-4 bg-black/80 backdrop-blur-md fixed top-0 z-50 flex justify-between items-center border-b border-white/10">
      <div className="flex items-center gap-8">
        <Link href="/" className="text-xl font-bold text-white hover:text-zinc-300 transition-colors">
          ⚙ ToolBank
        </Link>
        <ul className="flex gap-6 text-sm">
          <li>
            <Link href="/tools" className="text-zinc-300 hover:text-white hover:underline transition-colors">
              Browse
            </Link>
          </li>
          <li>
            <Link href="/admin/drift" className="text-zinc-300 hover:text-white hover:underline transition-colors">
              Drift
            </Link>
          </li>
        </ul>
      </div>
      <div className="flex items-center gap-4">
        <Link
          href="#scrape"
          className="px-4 py-2 text-sm font-medium bg-white text-black rounded-lg hover:bg-zinc-200 transition-colors"
        >
          Scrape Tool
        </Link>
        <ThemeToggle />
      </div>
    </nav>
  );
}
