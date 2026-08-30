import {
  BellIcon,
  BookIcon,
  GitBranchIcon,
  ChevronDownIcon,
  CodeIcon,
  CommentDiscussionIcon,
  GitPullRequestIcon,
  HistoryIcon,
  IssueOpenedIcon,
  KebabHorizontalIcon,
  LawIcon,
  MarkGithubIcon,
  PlayIcon,
  PlusIcon,
  RepoIcon,
  SearchIcon,
  ShieldLockIcon,
  StarIcon,
} from '@primer/octicons-react';

const files = [
  { name: '.github', message: 'Refine issue templates and CI defaults', age: '3 days ago', folder: true },
  { name: 'apps', message: 'Add provider-neutral application shells', age: '2 hours ago', folder: true },
  { name: 'packages', message: 'Generate API contract types', age: '2 hours ago', folder: true },
  { name: '.gitignore', message: 'Ignore local databases and reference captures', age: '4 days ago' },
  { name: 'LICENSE', message: 'License project under MIT', age: '4 days ago' },
  { name: 'README.md', message: 'Document the HubGit architecture', age: '2 hours ago' },
  { name: 'docker-compose.yml', message: 'Add one-command development stack', age: 'yesterday' },
];

const tabs = [
  ['Code', CodeIcon],
  ['Issues', IssueOpenedIcon, '12'],
  ['Pull requests', GitPullRequestIcon, '4'],
  ['Discussions', CommentDiscussionIcon],
  ['Pipelines', PlayIcon],
  ['Projects', RepoIcon],
  ['Security', ShieldLockIcon],
] as const;

export default function Home() {
  return (
    <div className="app-shell">
      <header className="global-header">
        <div className="header-leading">
          <button className="icon-button menu-button" aria-label="Open navigation menu">
            <span /><span /><span />
          </button>
          <a className="brand-mark" href="#" aria-label="HubGit home"><MarkGithubIcon size={32} /></a>
          <nav className="breadcrumbs" aria-label="Repository breadcrumb">
            <a href="#">not-the-ccp</a><span>/</span><a href="#"><strong>hubgit-ui</strong></a>
          </nav>
        </div>
        <div className="header-actions">
          <button className="search-button"><SearchIcon size={16} /><span>Type <kbd>/</kbd> to search</span></button>
          <span className="header-separator" />
          <button className="icon-button" aria-label="Create new"><PlusIcon size={16} /><ChevronDownIcon size={12} /></button>
          <button className="icon-button" aria-label="Issues"><IssueOpenedIcon size={17} /></button>
          <button className="icon-button" aria-label="Pull requests"><GitPullRequestIcon size={17} /></button>
          <button className="icon-button notification" aria-label="Notifications"><BellIcon size={17} /><span /></button>
          <button className="avatar" aria-label="Open profile menu">M</button>
        </div>
      </header>

      <div className="repo-navigation-wrap">
        <nav className="repo-navigation" aria-label="Repository navigation">
          {tabs.map(([label, Icon, count], index) => (
            <a className={index === 0 ? 'repo-tab active' : 'repo-tab'} href="#" key={label}>
              <Icon size={16} /><span>{label}</span>{count && <span className="counter">{count}</span>}
            </a>
          ))}
        </nav>
      </div>

      <main className="repo-page">
        <section className="repo-title-row">
          <div className="repo-title"><RepoIcon size={18} /><h1><a href="#">hubgit-ui</a></h1><span className="visibility">Public</span></div>
          <div className="repo-actions">
            <button><BellIcon size={16} />Watch <span className="button-count">3</span><ChevronDownIcon size={12} /></button>
            <button><GitBranchIcon size={16} />Fork <span className="button-count">0</span></button>
            <button><StarIcon size={16} />Star <span className="button-count">18</span></button>
          </div>
        </section>

        <div className="repo-grid">
          <section className="repository-content">
            <div className="content-toolbar">
              <button className="branch-button"><GitBranchIcon size={16} /><strong>main</strong><ChevronDownIcon size={12} /></button>
              <div className="ref-links"><a href="#"><GitBranchIcon size={16} /><strong>3</strong> Branches</a><a href="#"><LawIcon size={16} /><strong>2</strong> Tags</a></div>
              <div className="toolbar-spacer" />
              <button>Go to file</button><button>Add file <ChevronDownIcon size={12} /></button><button className="primary-button">&lt;&gt; Code <ChevronDownIcon size={12} /></button>
            </div>

            <div className="file-panel">
              <div className="latest-commit">
                <div className="avatar small">M</div><a href="#"><strong>not-the-ccp</strong></a>
                <a className="commit-message" href="#">Build the first complete HubGit product slice</a>
                <span className="commit-meta">a21bd77 · 2 hours ago</span>
                <a className="history-link" href="#"><HistoryIcon size={16} /><strong>24</strong> Commits</a>
              </div>
              <div className="file-table" role="table" aria-label="Files">
                {files.map((file) => (
                  <div className="file-row" role="row" key={file.name}>
                    <div className="file-name" role="cell">{file.folder ? <RepoIcon size={16} /> : <BookIcon size={16} />}<a href="#">{file.name}</a></div>
                    <a className="file-message" role="cell" href="#">{file.message}</a><span className="file-age" role="cell">{file.age}</span>
                  </div>
                ))}
              </div>
            </div>

            <article className="readme-panel">
              <div className="readme-header"><BookIcon size={16} /><strong>README.md</strong><button className="icon-button" aria-label="README options"><KebabHorizontalIcon size={16} /></button></div>
              <div className="readme-content">
                <div className="product-logo"><MarkGithubIcon size={38} /><span>HubGit</span></div>
                <h2>HubGit UI</h2><p>A provider-neutral, near-pixel-perfect GitHub frontend for self-hosted Git servers.</p>
                <div className="badges"><span>build passing</span><span>MIT licensed</span><span>React 19</span></div>
                <h3>What is this?</h3><p>HubGit recreates the familiar GitHub collaboration experience with an original implementation, an adapter-ready API, and a deterministic local backend.</p>
              </div>
            </article>
          </section>

          <aside className="repo-sidebar">
            <section><h2>About</h2><p>A clean-room GitHub-style frontend backed by a generic API and stateful mock server.</p><a href="#">hubgit-ui.dev</a><div className="topic-list"><span>git</span><span>react</span><span>fastapi</span><span>primer</span></div></section>
            <section><h2>Releases</h2><a className="release" href="#"><strong>HubGit preview 0.1.0</strong><span>Latest · yesterday</span></a><a href="#">+ 2 releases</a></section>
            <section><h2>Languages</h2><div className="language-bar"><span /><span /><span /></div><div className="languages"><span><i className="ts" />TypeScript 62.4%</span><span><i className="py" />Python 35.1%</span><span><i className="css" />CSS 2.5%</span></div></section>
          </aside>
        </div>
      </main>
    </div>
  );
}
