import './globals.css';
import type { Metadata } from 'next';
import { Inter, Outfit } from 'next/font/google';
import Sidebar from '@/components/Sidebar';
import { cn } from '@/lib/utils';
import { ToastProvider } from '@/components/Toast';
import { getTheme } from '@/themes';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const outfit = Outfit({ subsets: ['latin'], variable: '--font-outfit' });

const theme = getTheme();

export const metadata: Metadata = {
  title: theme.metaTitle,
  description: theme.metaDescription,
};

import { NatsProvider } from '@/lib/nats-context';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" data-edition={theme.edition} suppressHydrationWarning>
      <head>
        {theme.cssOverridePath && (
          <link rel="stylesheet" href={theme.cssOverridePath} />
        )}
      </head>
      <body className={cn(
        "min-h-screen bg-background font-sans antialiased overflow-hidden",
        inter.variable,
        outfit.variable
      )}>
        <NatsProvider>
          <ToastProvider>
            <div className="flex h-screen bg-[url('/grid-pattern.svg')] bg-fixed">
               {/* Global background effects */}
               <div className="fixed inset-0 bg-background/90 -z-50" />
               <div className={cn("fixed top-0 left-0 right-0 h-[500px] blur-[120px] rounded-full mix-blend-screen pointer-events-none -z-40", theme.glowColors.top)} />
               <div className={cn("fixed bottom-0 right-0 w-[500px] h-[500px] blur-[120px] rounded-full mix-blend-screen pointer-events-none -z-40", theme.glowColors.bottom)} />

              <Sidebar />

              <main className="flex-1 overflow-y-auto relative z-10 p-6 md:p-8">
                <div className="mx-auto max-w-7xl animate-fade-in">
                  {children}
                </div>
              </main>
            </div>
          </ToastProvider>
        </NatsProvider>
      </body>
    </html>
  );
}
