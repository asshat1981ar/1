import '../globals.css';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export const metadata = {
  title: 'ToolBank',
  description: 'Discover and scrape tools from across the web. One registry, every source.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-black text-white font-sans">
        <Navbar />
        <main className="mt-24">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
