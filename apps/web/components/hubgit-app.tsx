'use client';

import { SyntheticEvent, useState } from 'react';
import {
  AlertIcon,
  BellIcon,
  BookIcon,
  GitBranchIcon,
  CheckCircleFillIcon,
  ChevronDownIcon,
  CodeIcon,
  CommentDiscussionIcon,
  DiffIcon,
  EyeIcon,
  FileCodeIcon,
  FileDirectoryFillIcon,
  FilterIcon,
  GitCommitIcon,
  GitMergeIcon,
  GitPullRequestIcon,
  HistoryIcon,
  IssueOpenedIcon,
  KebabHorizontalIcon,
  LinkExternalIcon,
  MarkGithubIcon,
  MarkGithubIcon as HubMarkIcon,
  MoonIcon,
  OrganizationIcon,
  PencilIcon,
  PeopleIcon,
  PlayIcon,
  PlusIcon,
  ProjectIcon,
  RepoForkedIcon,
  RepoIcon,
  SearchIcon,
  ShieldCheckIcon,
  ShieldLockIcon,
  SmileyIcon,
  StarIcon,
  SunIcon,
  TagIcon,
  XCircleFillIcon,
} from '@primer/octicons-react';

type Branding = 'hubgit' | 'github-reference';
type Viewer = 'guest' | 'member' | 'admin';

const repoTabs = [
  ['Code', '', CodeIcon],
  ['Issues', 'issues', IssueOpenedIcon, '12'],
  ['Pull requests', 'pulls', GitPullRequestIcon, '4'],
  ['Discussions', 'discussions', CommentDiscussionIcon],
  ['Pipelines', 'actions', PlayIcon],
  ['Projects', 'projects', ProjectIcon],
  ['Security', 'security', ShieldLockIcon],
  ['Insights', 'pulse', GraphIcon],
] as const;

function GraphIcon({ size = 16 }: { size?: number }) {
  return <span aria-hidden="true" style={{ width: size, height: size, display: 'inline-flex', alignItems: 'end', gap: 1 }}><i style={{ height: '45%' }} /><i style={{ height: '80%' }} /><i style={{ height: '62%' }} /></span>;
}

const files = [
  ['.github', 'Refine issue templates and CI defaults', '3 days ago', true],
  ['apps', 'Add provider-neutral application shells', '2 hours ago', true],
  ['docs', 'Document clean-room fidelity workflow', 'yesterday', true],
  ['packages', 'Generate API contract types', '2 hours ago', true],
  ['.gitignore', 'Ignore local databases and reference captures', '4 days ago'],
  ['LICENSE', 'License project under MIT', '4 days ago'],
  ['README.md', 'Document the HubGit architecture', '2 hours ago'],
  ['docker-compose.yml', 'Add one-command development stack', 'yesterday'],
] as const;

const issues = [
  ['Add keyboard navigation to the ref selector', '#42 opened 2 hours ago by octocat', ['accessibility', 'frontend']],
  ['Large unified diffs lose the selected line after virtualization', '#38 opened yesterday by monalisa', ['bug', 'diffs']],
  ['Support capability discovery for provider adapters', '#31 opened 3 days ago by hubot', ['api', 'enhancement']],
  ['Document the Forgejo adapter conformance suite', '#27 opened last week by not-the-ccp', ['documentation']],
] as const;

const pulls = [
  ['Build provider-neutral repository overview payload', '#57 opened 3 hours ago by monalisa', 'Checks passing'],
  ['Add split and unified diff layouts', '#54 opened yesterday by octocat', 'Review required'],
  ['Create deterministic workflow run fixtures', '#49 opened 4 days ago by hubot', '1 check failing'],
] as const;

const navPath = (suffix = '') => `/not-the-ccp/hubgit-ui${suffix ? `/${suffix}` : ''}`;

export function HubGitApp({ initialPath = '/' }: { initialPath?: string }) {
  const [branding, setBranding] = useState<Branding>('hubgit');
  const [viewer, setViewer] = useState<Viewer>(initialPath === '/login' || initialPath === '/join' ? 'guest' : 'member');
  const [dark, setDark] = useState(false);
  const [query, setQuery] = useState('');

  const path = initialPath.replace(/\/+$/, '') || '/';
  const authRoute = ['/login', '/join', '/password-reset', '/verify', '/two-factor'].includes(path);
  const productName = branding === 'github-reference' ? 'GitHub reference' : 'HubGit';

  if (authRoute) {
    return <AuthPage mode={path.slice(1)} branding={branding} setBranding={setBranding} onLogin={() => setViewer('member')} />;
  }

  return (
    <div className={`hubgit-app ${dark ? 'theme-dark' : ''}`}>
      <GlobalHeader branding={branding} viewer={viewer} query={query} setQuery={setQuery} dark={dark} setDark={setDark} productName={productName} />
      {path === '/' || path === '/dashboard' ? <Dashboard /> : null}
      {path === '/issues' ? <GlobalQueue title="Issues" kind="issue" /> : null}
      {path === '/pulls' ? <GlobalQueue title="Pull requests" kind="pull" /> : null}
      {path === '/notifications' ? <Notifications /> : null}
      {path.startsWith('/search') ? <SearchResults query={query || 'adapter API'} /> : null}
      {path === '/not-the-ccp' ? <ProfilePage /> : null}
      {path === '/orgs/lcaml-foundation' ? <OrganizationPage /> : null}
      {path.startsWith('/settings') ? <SettingsPage scope="user" /> : null}
      {path.startsWith('/not-the-ccp/hubgit-ui/settings') ? <SettingsPage scope="repository" /> : null}
      {isRepoPath(path) && !path.startsWith('/not-the-ccp/hubgit-ui/settings') ? <RepositoryShell path={path} viewer={viewer} /> : null}
      <footer className="site-footer"><HubMarkIcon size={24} /><span>© 2026 HubGit contributors</span><a href="/">Terms</a><a href="/">Privacy</a><a href="/">Docs</a><a href="/">API</a><a href="/">Status</a></footer>
    </div>
  );
}

function isRepoPath(path: string) {
  return path === '/not-the-ccp/hubgit-ui' || path.startsWith('/not-the-ccp/hubgit-ui/');
}

function GlobalHeader({ branding, viewer, query, setQuery, dark, setDark, productName }: {
  branding: Branding; viewer: Viewer; query: string; setQuery: (v: string) => void; dark: boolean; setDark: (v: boolean) => void; productName: string;
}) {
  return (
    <header className="global-header">
      <div className="header-leading">
        <button className="icon-button menu-button" aria-label="Open navigation menu"><span /><span /><span /></button>
        <a className="brand-mark" href="/" aria-label={`${productName} home`}><MarkGithubIcon size={32} /></a>
        <a className="product-wordmark" href="/">{branding === 'github-reference' ? 'GitHub' : 'HubGit'}</a>
      </div>
      <div className="header-actions">
        <form className="search-form" action="/search"><SearchIcon size={16} /><input name="q" aria-label="Search HubGit" placeholder="Type / to search" value={query} onChange={(event) => setQuery(event.target.value)} /><kbd>/</kbd></form>
        <span className="header-separator" />
        <a className="icon-button" href="/issues" aria-label="Issues"><IssueOpenedIcon size={17} /></a>
        <a className="icon-button" href="/pulls" aria-label="Pull requests"><GitPullRequestIcon size={17} /></a>
        <a className="icon-button notification" href="/notifications" aria-label="Notifications"><BellIcon size={17} /><span /></a>
        <button className="icon-button" aria-label="Toggle color mode" onClick={() => setDark(!dark)}>{dark ? <SunIcon size={17} /> : <MoonIcon size={17} />}</button>
        {viewer === 'guest' ? <a className="header-signin" href="/login">Sign in</a> : <a className="avatar" href="/not-the-ccp" aria-label="Open profile">M</a>}
      </div>
    </header>
  );
}

function AuthPage({ mode, branding, setBranding, onLogin }: { mode: string; branding: Branding; setBranding: (v: Branding) => void; onLogin: () => void }) {
  const title = mode === 'join' ? 'Create your account' : mode === 'password-reset' ? 'Reset your password' : mode === 'two-factor' ? 'Two-factor authentication' : mode === 'verify' ? 'Verify your email' : 'Sign in to HubGit';
  const submit = (event: SyntheticEvent<HTMLFormElement>) => { event.preventDefault(); onLogin(); window.location.href = '/dashboard'; };
  return (
    <main className="auth-page">
      {branding === 'github-reference' && <div className="reference-warning"><AlertIcon size={24} /><div><strong>THIS IS NOT GITHUB</strong><span>Educational HubGit clone. Credentials are local to this demo and are never sent to GitHub.</span></div></div>}
      <div className="auth-brand"><MarkGithubIcon size={48} /><strong>{branding === 'github-reference' ? 'GitHub reference' : 'HubGit'}</strong></div>
      <section className="auth-card">
        <h1>{title}</h1>
        {mode === 'verify' ? <><p>A verification link for this local demo was sent to <strong>monalisa@hubgit.test</strong>.</p><button className="primary-button wide">Open development mailbox</button></> : (
          <form onSubmit={submit}>
            {mode === 'join' && <><label htmlFor="name">Username</label><input id="name" defaultValue="monalisa" /><label htmlFor="email">Email address</label><input id="email" type="email" defaultValue="monalisa@hubgit.test" /></>}
            {mode !== 'password-reset' && mode !== 'two-factor' && <><label htmlFor="login">Username or email address</label><input id="login" autoComplete="username" defaultValue="monalisa" /></>}
            {mode === 'two-factor' ? <><label htmlFor="otp">Authentication code</label><input id="otp" inputMode="numeric" placeholder="000000" /></> : <><label htmlFor="password">{mode === 'password-reset' ? 'Email address' : 'Password'}</label><input id="password" type={mode === 'password-reset' ? 'email' : 'password'} autoComplete="current-password" defaultValue={mode === 'password-reset' ? 'monalisa@hubgit.test' : 'hubgit-demo'} /></>}
            <button className="primary-button wide" type="submit">{mode === 'join' ? 'Create account' : mode === 'password-reset' ? 'Send reset link' : 'Continue'}</button>
          </form>
        )}
      </section>
      <div className="auth-secondary">{mode === 'login' ? <>New to HubGit? <a href="/join">Create an account</a></> : <a href="/login">Return to sign in</a>}</div>
      <button className="brand-switch" onClick={() => setBranding(branding === 'hubgit' ? 'github-reference' : 'hubgit')}>Preview {branding === 'hubgit' ? 'GitHub reference' : 'HubGit'} branding</button>
    </main>
  );
}

function Dashboard() {
  return (
    <main className="dashboard-layout page-width">
      <aside className="dashboard-sidebar">
        <div className="section-title"><h2>Top repositories</h2><button className="primary-button"><PlusIcon size={14} /> New</button></div>
        <input className="filter-input" placeholder="Find a repository…" />
        {['not-the-ccp/hubgit-ui', 'lcaml-foundation/caramel', 'not-the-ccp/avelune', 'lcaml-foundation/ouroboros'].map((repo) => <a className="repo-list-link" href={`/${repo}`} key={repo}><RepoIcon size={16} />{repo}</a>)}
        <h3>Your teams</h3><a className="repo-list-link" href="/orgs/lcaml-foundation"><PeopleIcon size={16} />lcaml-foundation/core</a>
      </aside>
      <section className="feed-column">
        <h1>Home</h1>
        <div className="dashboard-tabs"><button className="active">For you</button><button>Following</button></div>
        <FeedCard actor="monalisa" action="pushed 3 commits to" target="not-the-ccp/hubgit-ui" />
        <FeedCard actor="octocat" action="opened pull request #57 in" target="not-the-ccp/hubgit-ui" />
        <FeedCard actor="hubot" action="released v0.1.0 in" target="not-the-ccp/hubgit-ui" />
      </section>
      <aside className="dashboard-aside"><section><h2>Latest changes</h2><p><time>2 hours ago</time> Visual regression baseline added for repository pages.</p><p><time>Yesterday</time> New API capability matrix is available.</p><a href="/">View changelog →</a></section><section><h2>Explore repositories</h2><strong>primer/react</strong><p>The React implementation of GitHub&apos;s design system.</p><span>TypeScript · 3.9k stars</span></section></aside>
    </main>
  );
}

function FeedCard({ actor, action, target }: { actor: string; action: string; target: string }) {
  return <article className="feed-card"><div className="avatar small">{actor[0].toUpperCase()}</div><div><p><strong>{actor}</strong> {action} <a href={`/${target}`}><strong>{target}</strong></a></p><div className="feed-repo"><RepoIcon size={18} /><strong>{target}</strong><span>Public</span><p>Provider-neutral Git collaboration frontend.</p><div><span className="language-dot" />TypeScript</div></div></div></article>;
}

function RepositoryShell({ path, viewer }: { path: string; viewer: Viewer }) {
  const suffix = path.replace('/not-the-ccp/hubgit-ui', '').replace(/^\//, '');
  const active = suffix.split('/')[0];
  return (
    <>
      <div className="repo-subheader page-width"><div className="repo-title"><RepoIcon size={18} /><a href={navPath()}><strong>not-the-ccp</strong> / <strong>hubgit-ui</strong></a><span className="visibility">Public</span></div><div className="repo-actions"><button><EyeIcon size={16} />Watch <b>3</b></button><button><RepoForkedIcon size={16} />Fork <b>0</b></button><button><StarIcon size={16} />Star <b>18</b></button></div></div>
      <nav className="repo-navigation" aria-label="Repository navigation">{repoTabs.map(([label, segment, Icon, count]) => <a className={active === segment || (!active && !segment) ? 'repo-tab active' : 'repo-tab'} href={navPath(segment)} key={label}><Icon size={16} /><span>{label}</span>{count && <span className="counter">{count}</span>}</a>)}</nav>
      <main className="repo-page page-width">
        {!active && <CodeView />}
        {active === 'issues' && (suffix.match(/^issues\/\d+/) ? <IssueDetail /> : <IssueList />)}
        {active === 'pulls' && (suffix.match(/^pulls\/\d+/) ? <PullDetail /> : <PullList />)}
        {active === 'commits' && <CommitHistory />}
        {active === 'commit' && <CommitDetail />}
        {active === 'branches' && <RefsPage kind="branches" />}
        {active === 'tags' && <RefsPage kind="tags" />}
        {active === 'releases' && <ReleasesPage />}
        {active === 'discussions' && <DiscussionsPage />}
        {active === 'actions' && <ActionsPage />}
        {active === 'projects' && <ProjectsPage />}
        {active === 'wiki' && <WikiPage />}
        {active === 'security' && <SecurityPage />}
        {active === 'pulse' && <InsightsPage />}
        {active === 'blob' && <BlobPage />}
        {active === 'compare' && <CommitDetail />}
        {active === 'settings' && viewer !== 'guest' && <SettingsPage scope="repository" />}
      </main>
    </>
  );
}

function CodeView() {
  return <div className="repo-grid"><section><div className="content-toolbar"><button className="branch-button"><GitBranchIcon size={16} /><strong>main</strong><ChevronDownIcon size={12} /></button><div className="ref-links"><a href={navPath('branches')}><GitBranchIcon size={16} /><strong>3</strong> Branches</a><a href={navPath('tags')}><TagIcon size={16} /><strong>2</strong> Tags</a></div><span className="toolbar-spacer" /><button>Go to file</button><button>Add file <ChevronDownIcon size={12} /></button><button className="primary-button">&lt;&gt; Code <ChevronDownIcon size={12} /></button></div><div className="file-panel"><div className="latest-commit"><div className="avatar small">M</div><strong>not-the-ccp</strong><a className="commit-message" href={navPath('commit/a21bd77')}>Build the first complete HubGit product slice</a><span>a21bd77 · 2 hours ago</span><a href={navPath('commits/main')}><HistoryIcon size={16} /> 24 commits</a></div>{files.map(([name, message, age, folder]) => <div className="file-row" key={name}><div className="file-name">{folder ? <FileDirectoryFillIcon size={16} /> : <FileCodeIcon size={16} />}<a href={folder ? navPath(`tree/main/${name}`) : navPath(`blob/main/${name}`)}>{name}</a></div><a className="file-message" href="/">{message}</a><span className="file-age">{age}</span></div>)}</div><Readme /></section><RepoSidebar /></div>;
}

function Readme() { return <article className="readme-panel"><div className="readme-header"><BookIcon size={16} /><strong>README.md</strong><KebabHorizontalIcon size={16} /></div><div className="readme-content"><div className="product-logo"><MarkGithubIcon size={38} /><span>HubGit</span></div><h2>HubGit UI</h2><p>A provider-neutral, near-pixel-perfect GitHub frontend for self-hosted Git servers.</p><div className="badges"><span>build passing</span><span>MIT licensed</span><span>React 19</span></div><h3>What is this?</h3><p>HubGit recreates the familiar Git collaboration experience with an original implementation, adapter-ready API, and deterministic local backend.</p><pre><code>docker compose up --build</code></pre></div></article>; }

function RepoSidebar() { return <aside className="repo-sidebar"><section><h2>About</h2><p>A clean-room GitHub-style frontend backed by a generic API and stateful mock server.</p><a href="/">hubgit-ui.dev <LinkExternalIcon size={12} /></a><div className="topic-list"><span>git</span><span>react</span><span>fastapi</span><span>primer</span></div></section><section><h2>Releases</h2><a href={navPath('releases')}><strong>HubGit preview 0.1.0</strong><br /><small>Latest · yesterday</small></a></section><section><h2>Languages</h2><div className="language-bar"><span /><span /><span /></div><p>TypeScript 62.4% · Python 35.1% · CSS 2.5%</p></section></aside>; }

function IssueList() { return <ListPage title="Issues" createLabel="New issue" search="is:issue is:open" items={issues.map(([title, meta, labels]) => ({ title, meta, labels: [...labels], icon: <IssueOpenedIcon className="state-open" size={16} />, href: navPath('issues/42') }))} />; }
function PullList() { return <ListPage title="Pull requests" createLabel="New pull request" search="is:pr is:open" items={pulls.map(([title, meta, status]) => ({ title, meta, labels: [status], icon: <GitPullRequestIcon className="state-open" size={16} />, href: navPath('pulls/57') }))} />; }

function ListPage({ title, createLabel, search, items }: { title: string; createLabel: string; search: string; items: { title: string; meta: string; labels: string[]; icon: React.ReactNode; href: string }[] }) {
  return <section className="list-page" aria-label={title}><div className="list-actions"><div className="query-builder"><FilterIcon size={16} /><input aria-label={`Search ${title}`} defaultValue={search} /></div><button>Labels</button><button>Milestones</button><button className="primary-button">{createLabel}</button></div><div className="list-panel"><div className="list-panel-header"><span><strong>{items.length} Open</strong></span><span>Closed</span><span className="toolbar-spacer" />Author <ChevronDownIcon size={12} /> Label <ChevronDownIcon size={12} /> Sort <ChevronDownIcon size={12} /></div>{items.map((item) => <article className="work-item" key={item.title}>{item.icon}<div><a href={item.href}><h2>{item.title}</h2></a><div className="label-row">{item.labels.map((label) => <span key={label}>{label}</span>)}</div><p>{item.meta}</p></div><span className="comment-count"><CommentDiscussionIcon size={16} /> 3</span></article>)}</div></section>;
}

function IssueDetail() { return <DetailPage kind="issue" title="Add keyboard navigation to the ref selector" number="42" state="Open" />; }
function PullDetail() { return <DetailPage kind="pull" title="Build provider-neutral repository overview payload" number="57" state="Open" />; }

function DetailPage({ kind, title, number, state }: { kind: 'issue' | 'pull'; title: string; number: string; state: string }) {
  return <section className="detail-page"><div className="detail-heading"><h1>{title} <span>#{number}</span></h1><button className="primary-button">New {kind === 'issue' ? 'issue' : 'pull request'}</button><p><span className="state-pill">{kind === 'issue' ? <IssueOpenedIcon size={16} /> : <GitPullRequestIcon size={16} />}{state}</span> monalisa opened this {kind} 2 hours ago · 3 comments</p></div>{kind === 'pull' && <nav className="detail-tabs"><a className="active" href="/"><CommentDiscussionIcon size={16} /> Conversation 3</a><a href="/"><GitCommitIcon size={16} /> Commits 2</a><a href="/"><CheckCircleFillIcon size={16} /> Checks 5</a><a href="/"><DiffIcon size={16} /> Files changed 8</a></nav>}<div className="conversation-grid"><div className="timeline"><Comment author="monalisa" body="This change introduces a single repository overview resource and keeps provider-specific response details behind the adapter ports." /><div className="timeline-event"><GitCommitIcon size={16} /><strong>monalisa</strong> added 2 commits</div><Comment author="octocat" body="The response shape looks good. I left one suggestion around capability flags and pagination." />{kind === 'pull' && <div className="merge-box"><CheckCircleFillIcon size={24} /><div><strong>All checks have passed</strong><p>2 approving reviews · branch is up to date</p></div><button className="primary-button"><GitMergeIcon size={16} /> Merge pull request</button></div>}</div><aside className="metadata-sidebar"><Metadata title="Assignees" value="monalisa" /><Metadata title="Labels" value="api · enhancement" /><Metadata title="Projects" value="HubGit 1.0" /><Metadata title="Milestone" value="Foundation" /><Metadata title="Development" value="2 linked branches" /></aside></div></section>;
}

function Comment({ author, body }: { author: string; body: string }) { return <article className="comment"><div className="avatar small">{author[0].toUpperCase()}</div><div><header><strong>{author}</strong> commented 2 hours ago <KebabHorizontalIcon size={16} /></header><div><p>{body}</p><pre><code>{`GET /api/v1/repos/{owner}/{repo}/overview?ref=main`}</code></pre><button><SmileyIcon size={16} /> 4</button></div></div></article>; }
function Metadata({ title, value }: { title: string; value: string }) { return <section><strong>{title}</strong><span>{value}</span></section>; }

function CommitHistory() { return <FeatureList heading="Commits" icon={<GitCommitIcon size={20} />} items={['Build the first complete HubGit product slice', 'Add provider-neutral OpenAPI models', 'Seed pull requests and workflow runs', 'Create responsive repository shell']} />; }
function CommitDetail() { return <section><div className="feature-heading"><div><h1>Build the first complete HubGit product slice</h1><p>Authored and committed by monalisa 2 hours ago</p></div><code>a21bd771e53</code></div><div className="diff-summary"><strong>8 files changed</strong><span className="additions">+427</span><span className="deletions">−18</span></div>{['apps/web/app/page.tsx', 'apps/api/app/main.py'].map((file) => <article className="diff-file" key={file}><header><DiffIcon size={16} /><strong>{file}</strong><span className="toolbar-spacer" />Viewed <ChevronDownIcon size={12} /></header><pre><span>@@ -1,4 +1,9 @@</span>{`\n`}<em>+ export const capabilities = await api.meta();</em>{`\n`} export function RepositoryPage() {'{'}{`\n`}<em>+   return &lt;RepositoryShell /&gt;;</em>{`\n`} {'}'}</pre></article>)}</section>; }
function RefsPage({ kind }: { kind: string }) { return <FeatureList heading={kind === 'tags' ? 'Tags' : 'Branches'} icon={kind === 'tags' ? <TagIcon size={20} /> : <GitBranchIcon size={20} />} items={kind === 'tags' ? ['v0.1.0 — HubGit preview', 'v0.0.2 — API foundation'] : ['main — Default', 'feature/provider-contract — Active', 'docs/fidelity-matrix — Active']} />; }
function ReleasesPage() { return <FeatureList heading="Releases" icon={<TagIcon size={20} />} items={['HubGit preview 0.1.0 · Latest', 'Contract foundation 0.0.2', 'Initial clean-room skeleton 0.0.1']} />; }
function DiscussionsPage() { return <FeatureList heading="Discussions" icon={<CommentDiscussionIcon size={20} />} items={['Welcome to HubGit Discussions', 'How should provider capabilities map to navigation?', 'Show and tell: custom instance themes']} />; }
function ActionsPage() { return <FeatureList heading="Pipelines" icon={<PlayIcon size={20} />} items={['CI · main · passing', 'Visual regression · pull/57 · in progress', 'Publish containers · v0.1.0 · passing']} statuses />; }
function ProjectsPage() {
  const columns = [
    { title: 'Backlog', cards: issues.slice(2) },
    { title: 'In progress', cards: issues.slice(0, 2) },
    { title: 'Done', cards: issues.slice(3) },
  ];
  return <section><div className="feature-heading"><h1>Projects</h1><button className="primary-button">New project</button></div><div className="project-board">{columns.map(({ title: column, cards }) => <section key={column}><h2>{column} <span>{cards.length}</span></h2>{cards.map(([title, meta]) => <article key={title}><IssueOpenedIcon size={15} /><strong>{title}</strong><small>{meta}</small></article>)}</section>)}</div></section>;
}
function WikiPage() { return <section className="wiki-layout"><article className="readme-content"><h1>HubGit Wiki</h1><p>Welcome to the project knowledge base.</p><h2>Architecture</h2><p>The browser consumes only the provider-neutral API. Adapters translate external Git-host data into the stable HubGit domain.</p><h2>Pages</h2><ul><li>Getting started</li><li>Adapter authoring</li><li>Fidelity workflow</li></ul></article><aside><button className="primary-button">New page</button><h3>Pages</h3><a href="/">Home</a><a href="/">Architecture</a><a href="/">Development</a></aside></section>; }
function SecurityPage() { return <FeatureList heading="Security and quality" icon={<ShieldCheckIcon size={20} />} items={['Security policy · Enabled', 'Private vulnerability reporting · Enabled', 'Dependabot alerts · 0 open', 'Code scanning · 2 passing analyses']} statuses />; }
function InsightsPage() { return <section><div className="feature-heading"><h1>Repository insights</h1></div><div className="insight-grid">{['Pulse', 'Contributors', 'Community standards', 'Commit activity', 'Code frequency', 'Network', 'Traffic'].map((item, index) => <article key={item}><GraphIcon size={24} /><h2>{item}</h2><strong>{index === 0 ? '24 updates' : `${12 + index * 7}`}</strong><div className="sparkline" /></article>)}</div></section>; }
function BlobPage() { const code = ['import { createApiClient } from "@hubgit/contracts";', '', 'export const api = createApiClient({', '  baseUrl: "/api/v1",', '});']; return <section><div className="blob-toolbar"><span>apps / web / src / api.ts</span><button>Raw</button><button><PencilIcon size={14} /> Edit</button></div><div className="code-view">{code.map((line, index) => <div key={index}><a href={`#L${index + 1}`}>{index + 1}</a><code>{line}</code></div>)}</div></section>; }

function FeatureList({ heading, icon, items, statuses }: { heading: string; icon: React.ReactNode; items: string[]; statuses?: boolean }) { return <section><div className="feature-heading"><div>{icon}<h1>{heading}</h1></div><button className="primary-button">New</button></div><div className="feature-list">{items.map((item, index) => <article key={item}>{statuses ? (index === 1 ? <XCircleFillIcon className="state-closed" size={18} /> : <CheckCircleFillIcon className="state-open" size={18} />) : icon}<div><strong>{item}</strong><p>Updated {index + 1} day{index ? 's' : ''} ago by monalisa</p></div><ChevronDownIcon size={14} /></article>)}</div></section>; }

function GlobalQueue({ title, kind }: { title: string; kind: 'issue' | 'pull' }) { return <main className="global-queue page-width"><h1>{title}</h1><div className="queue-tabs"><a className="active" href="/">Created</a><a href="/">Assigned</a><a href="/">Mentioned</a><a href="/">Review requests</a></div>{kind === 'issue' ? <IssueList /> : <PullList />}</main>; }

function Notifications() { return <main className="notifications-layout page-width"><aside><h2>Inbox</h2><a className="active" href="/">Inbox <span>4</span></a><a href="/">Saved</a><a href="/">Done</a><h3>Repositories</h3><a href="/">not-the-ccp/hubgit-ui</a><a href="/">primer/react</a></aside><section><div className="feature-heading"><h1>Notifications</h1><button>Mark all as read</button></div><div className="notification-filters"><button>All</button><button>Unread</button><button>Participating</button><span className="toolbar-spacer" /><button><FilterIcon size={14} /> Filter</button></div><FeatureList heading="Today" icon={<BellIcon size={18} />} items={['Review requested: provider-neutral overview payload', 'Issue assigned: keyboard navigation', 'Workflow completed: CI on main', 'New release: HubGit preview 0.1.0']} /></section></main>; }

function SearchResults({ query }: { query: string }) { return <main className="search-layout page-width"><aside><h2>Filter by</h2>{['Code', 'Repositories', 'Issues', 'Pull requests', 'Discussions', 'Users', 'Commits', 'Wiki'].map((filter, index) => <a className={index === 0 ? 'active' : ''} href="/" key={filter}>{filter}<span>{12 - index}</span></a>)}</aside><section><h1>Search results for <strong>{query}</strong></h1><div className="query-builder"><SearchIcon size={16} /><input value={query} readOnly /><button className="primary-button">Search</button></div><FeatureList heading="12 results" icon={<FileCodeIcon size={18} />} items={['packages/contracts/openapi.json', 'apps/api/app/adapters/base.py', 'apps/web/features/repositories/api.ts', 'docs/adapter-architecture.md']} /></section></main>; }

function ProfilePage() { return <main className="profile-page page-width"><aside><div className="profile-avatar">M</div><h1>Monalisa Octocat</h1><span>not-the-ccp</span><p>Building delightful developer tools and clean-room interfaces.</p><button>Edit profile</button><p><PeopleIcon size={16} /> <strong>128</strong> followers · <strong>42</strong> following</p><p><OrganizationIcon size={16} /> lcaml-foundation</p></aside><section><nav className="profile-tabs"><a className="active" href="/">Overview</a><a href="/">Repositories 18</a><a href="/">Projects</a><a href="/">Stars 96</a></nav><h2>Popular repositories</h2><div className="pinned-grid">{['hubgit-ui', 'avelune', 'git-sha1-cuda', 'voice-thingie'].map((repo) => <article key={repo}><a href={repo === 'hubgit-ui' ? navPath() : '#'}><strong>{repo}</strong></a><span>Public</span><p>Open-source experiments and useful developer tooling.</p><small><i /> TypeScript · ★ 18</small></article>)}</div><h2>312 contributions in the last year</h2><div className="contribution-grid">{Array.from({ length: 182 }, (_, i) => <i key={i} data-level={(i * 7 + 3) % 5} />)}</div></section></main>; }

function OrganizationPage() { return <main className="organization-page page-width"><header><div className="org-avatar">LC</div><div><h1>LCaml Foundation</h1><p>Open-source tools for language and compiler developers.</p><a href="/">lcaml.org</a></div></header><nav className="profile-tabs"><a className="active" href="/">Overview</a><a href="/">Repositories 24</a><a href="/">Projects</a><a href="/">Packages</a><a href="/">People 16</a><a href="/">Teams 5</a></nav><div className="org-grid"><section><h2>Pinned repositories</h2><div className="pinned-grid">{['caramel', 'ouroboros', 'lccolor', 'stdlib'].map((repo) => <article key={repo}><a href="/"><strong>{repo}</strong></a><span>Public</span><p>Production-ready open source from LCaml Foundation.</p></article>)}</div></section><aside><h2>People</h2><div className="avatar-stack">MOHLCAS</div><a href="/">View all members</a><h2>Top languages</h2><p>OCaml · Rust · TypeScript</p></aside></div></main>; }

function SettingsPage({ scope }: { scope: 'user' | 'repository' }) { const groups = scope === 'user' ? ['Public profile', 'Account', 'Appearance', 'Accessibility', 'Notifications', 'Emails', 'Password and authentication', 'SSH and GPG keys', 'Developer settings'] : ['General', 'Collaborators and teams', 'Rules', 'Actions', 'Webhooks', 'Deploy keys', 'Secrets and variables', 'Pages']; return <main className="settings-layout page-width"><aside><h2>{scope === 'user' ? 'Personal settings' : 'Repository settings'}</h2>{groups.map((item, index) => <a className={index === 0 ? 'active' : ''} href="/" key={item}>{item}</a>)}</aside><section><h1>{groups[0]}</h1><div className="settings-section"><h2>{scope === 'user' ? 'Profile information' : 'Repository name'}</h2><label>Display name<input defaultValue={scope === 'user' ? 'Monalisa Octocat' : 'hubgit-ui'} /></label><label>Bio<textarea defaultValue="A provider-neutral Git collaboration frontend." /></label><button className="primary-button">Save changes</button></div><div className="settings-section"><h2>Features</h2>{['Issues', 'Discussions', 'Projects', 'Wiki', 'Pipelines'].map((feature) => <label className="check-row" key={feature}><input type="checkbox" defaultChecked /> <strong>{feature}</strong><span>Enable the {feature.toLowerCase()} module.</span></label>)}</div>{scope === 'repository' && <div className="danger-zone"><h2>Danger Zone</h2><div><span><strong>Archive this repository</strong><small>Make the repository read-only.</small></span><button>Archive</button></div><div><span><strong>Delete this repository</strong><small>Permanently remove repository data.</small></span><button>Delete</button></div></div>}</section></main>; }
