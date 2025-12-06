import { Sidebar } from '@/components/layout/Sidebar';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { getSession } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { redirect } from 'next/navigation';

export const dynamic = 'force-dynamic';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();

  if (!session) {
    redirect('/login');
  }

  const zone = await prisma.zone.findFirst({
    where: { userId: session.id },
    select: { id: true },
  });

  const settings = zone
    ? await prisma.settings.findUnique({
        where: { zoneId: zone.id },
        select: { language: true },
      })
    : null;

  const initialLanguage = (settings?.language as 'de' | 'en') || 'de';

  return (
    <LanguageProvider initialLanguage={initialLanguage}>
      <div className="flex h-screen bg-gradient-to-br from-black via-gray-900 to-black overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <div className="p-8 md:p-8 pt-16 md:pt-8">{children}</div>
        </main>
      </div>
    </LanguageProvider>
  );
}
