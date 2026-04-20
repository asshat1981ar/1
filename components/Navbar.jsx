export function Navbar() {
  return (
    <nav className="w-full px-4 py-6 bg-black/80 backdrop-blur-md fixed top-0 z-50 flex justify-between items-center border-b border-white/10">
      <h1 className="text-xl font-bold text-white">⚙ ToolBank</h1>
      <ul className="flex gap-6 text-sm">
        <li><a href="#discover" className="hover:underline">Discover</a></li>
        <li><a href="#sources" className="hover:underline">Sources</a></li>
        <li><a href="#scrape" className="hover:underline">Scrape</a></li>
      </ul>
    </nav>
  );
}
