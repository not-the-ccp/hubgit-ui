import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'HubGit UI · A provider-neutral Git frontend',
  description: 'A clean-room, GitHub-faithful frontend for self-hosted Git servers.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
