import './globals.css';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { ThemeProvider } from 'next-themes';
import { TrackingPixel } from '../components/TrackingPixel';

export const metadata = {
  title: 'ToolBank',
  description: 'Discover and scrape tools from across the web. One registry, every source.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-white dark:bg-black text-zinc-900 dark:text-white font-sans transition-colors">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <TrackingPixel />
          <Navbar />
          <main className="mt-24">{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
