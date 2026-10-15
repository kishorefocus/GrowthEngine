/**
 * Root admin layout — minimal wrapper.
 * - /admin/login and /admin/register render full-page (no sidebar)
 * - /admin/(shell)/* pages use the (shell)/layout.tsx which adds sidebar+topbar
 */
export default function AdminRootLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
