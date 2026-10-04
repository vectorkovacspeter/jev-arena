import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ChevronRight, Maximize2, Minimize2, PanelLeftClose, PanelLeftOpen, type LucideIcon } from 'lucide-react';
import '@fontsource/poppins/latin-400.css';
import '@fontsource/poppins/latin-500.css';
import '@fontsource/poppins/latin-600.css';
import '@fontsource/poppins/latin-700.css';
import logo from './taia-logo.webp?inline';
import './app-shell.css';

export type AppNavigationItem<Id extends string> = {
  id: Id;
  label: string;
  icon: LucideIcon;
};

export type ShellLabels = {
  skipToContent: string; expandNavigation: string; collapseNavigation: string; presenter: string;
  exitPresenter: string; exitPresenterTitle: string; presenterTitle: string; workspace: string;
  localWorkspace: string; homeLabel: string; workspaceLabel: string; navigationLabel: string;
};

type AppShellProps<Id extends string> = {
  appName: string;
  description: string;
  navigation: readonly AppNavigationItem<Id>[];
  activePage: Id;
  onNavigate: (page: Id) => void;
  presenter: boolean;
  onPresenterChange: (presenter: boolean) => void;
  status: string;
  statusTone?: 'neutral' | 'success';
  sidebarFooter?: ReactNode;
  footerNote: ReactNode;
  labels: ShellLabels;
  headerExtra?: ReactNode;
  className?: string;
  children: ReactNode;
};

const navigationPreference = 'taia:navigation-collapsed';
// Brand name: never translated.
const brandName = 'The AI Automators';

/** Shared frame for TAIA micro-apps. Keep application workflows in children. */
export function AppShell<Id extends string>({
  appName, description, navigation, activePage, onNavigate, presenter,
  onPresenterChange, status, statusTone = 'neutral', sidebarFooter,
  footerNote, labels, headerExtra, className = '', children,
}: AppShellProps<Id>) {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(navigationPreference) === 'true'; }
    catch { return false; }
  });
  const navRef = useRef<HTMLElement>(null);
  const currentPage = navigation.find(item => item.id === activePage);

  useEffect(() => {
    if (!presenter) return;
    const exit = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onPresenterChange(false);
    };
    window.addEventListener('keydown', exit);
    return () => window.removeEventListener('keydown', exit);
  }, [presenter, onPresenterChange]);

  useEffect(() => {
    const nav = navRef.current;
    const active = nav?.querySelector<HTMLElement>('[aria-current="page"]');
    if (!nav || !active || nav.scrollWidth <= nav.clientWidth) return;
    // Keep the current destination visible in the mobile navigation strip.
    nav.scrollLeft = active.offsetLeft - nav.offsetLeft - (nav.clientWidth - active.offsetWidth) / 2;
  }, [activePage, presenter]);

  function toggleNavigation() {
    const next = !collapsed;
    setCollapsed(next);
    // Saved HTML reports and privacy-restricted browsers can deny storage.
    try { localStorage.setItem(navigationPreference, String(next)); } catch { /* Session-only preference. */ }
  }

  function navigate(page: Id) {
    onNavigate(page);
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  return <div className={`taia-shell ${collapsed ? 'taia-shell--collapsed' : ''} ${presenter ? 'taia-shell--presenter presenter' : ''} ${className}`}>
    <a className="taia-skip-link" href="#taia-main">{labels.skipToContent}</a>
    <header className="taia-header">
      <a className="taia-brand" href="#" aria-label={labels.homeLabel} onClick={event => { event.preventDefault(); if (navigation[0]) navigate(navigation[0].id); }}>
        <span className="taia-logo-crop"><img src={logo} alt="The AI Automators" /></span>
      </a>
      <div className="taia-header-content">
        {!presenter && <button type="button" className="taia-icon-button taia-nav-toggle" onClick={toggleNavigation} aria-label={collapsed ? labels.expandNavigation : labels.collapseNavigation} title={collapsed ? labels.expandNavigation : labels.collapseNavigation} aria-expanded={!collapsed} aria-controls="taia-navigation">
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>}
        <div className="taia-location"><strong>{appName}</strong><ChevronRight size={14} aria-hidden="true" /><span>{currentPage?.label}</span></div>
        <div className="taia-header-actions">
          {headerExtra}
          <span className={`taia-status taia-status--${statusTone}`}><i aria-hidden="true" />{status}</span>
          <button type="button" className="taia-presenter-button" aria-pressed={presenter} onClick={() => onPresenterChange(!presenter)} title={presenter ? labels.exitPresenterTitle : labels.presenterTitle}>
            {presenter ? <Minimize2 size={16} /> : <Maximize2 size={16} />}<span>{presenter ? labels.exitPresenter : labels.presenter}</span>
          </button>
        </div>
      </div>
    </header>
    <aside className="taia-sidebar" aria-label={labels.workspaceLabel}>
      <div className="taia-sidebar-intro"><span>{labels.workspace}</span><p>{description}</p></div>
      <nav id="taia-navigation" className="taia-navigation" aria-label={labels.navigationLabel} ref={navRef}>
        {navigation.map(({ id, label, icon: Icon }) => <button type="button" key={id} onClick={() => navigate(id)} aria-current={activePage === id ? 'page' : undefined} title={label} aria-label={label}>
          <Icon size={18} aria-hidden="true" /><span>{label}</span>
        </button>)}
      </nav>
      <div className="taia-sidebar-footer">{sidebarFooter}<span className="taia-workspace-label"><i aria-hidden="true" />{labels.localWorkspace}</span></div>
    </aside>
    <div className="taia-body">
      <main id="taia-main" className="taia-content" tabIndex={-1}>{children}</main>
      <footer className="taia-footer"><span>{brandName} <span>/</span> {appName}</span><span>{footerNote}</span></footer>
    </div>
  </div>;
}
