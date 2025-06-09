export function Navbar() {
  return (
    <nav className="w-full px-4 py-6 bg-black/80 backdrop-blur-md fixed top-0 z-50 flex justify-between items-center border-b border-white/10">
      <h1 className="text-xl font-bold text-white">No-Bull</h1>
      <ul className="flex gap-6 text-sm">
        <li><a href="#services" className="hover:underline">Services</a></li>
        <li><a href="#work" className="hover:underline">Work</a></li>
        <li><a href="#contact" className="hover:underline">Contact</a></li>
      </ul>
    </nav>
  );
}