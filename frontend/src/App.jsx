import React, { createContext, useContext, useEffect, useState } from 'react';



import { Routes, Route, Navigate, Link, useNavigate, useLocation } from 'react-router-dom';



import { Bug, LayoutDashboard, FolderKanban, ListChecks, LogOut, Plus, ShieldCheck, Activity, BrainCircuit, Menu, X, UploadCloud, FileArchive, CheckCircle2 } from 'lucide-react';



import api, {
  messageOf,
  downloadProjectTestReportExcel
} from './api';


const AuthContext = createContext(null);



const useAuth = () => useContext(AuthContext);



function AuthProvider({ children }) { const [user, setUser] = useState(() => { try { return JSON.parse(localStorage.getItem('bug_detective_user')) } catch { return null } }); const [token, setToken] = useState(() => localStorage.getItem('bug_detective_token')); const login = (data) => { localStorage.setItem('bug_detective_token', data.access_token); localStorage.setItem('bug_detective_user', JSON.stringify(data.user)); setToken(data.access_token); setUser(data.user) }; const logout = () => { localStorage.removeItem('bug_detective_token'); localStorage.removeItem('bug_detective_user'); setToken(null); setUser(null) }; return <AuthContext.Provider value={{ user, token, login, logout }}>{children}</AuthContext.Provider> }



function Protected({ children }) { const { token } = useAuth(); return token ? children : <Navigate to="/login" replace /> }



function Shell({ children }) { const { user, logout } = useAuth(); const [mobile, setMobile] = useState(false); const loc = useLocation(); const nav = [['/', 'Dashboard', LayoutDashboard], ['/projects', 'Projects', FolderKanban], ['/upload', 'Upload Project', UploadCloud], ['/bugs', 'Bugs', Bug], ['/tests', 'Test Cases', ListChecks]]; return <div className="shell"><aside className={`sidebar ${mobile ? 'show' : ''}`}><div className="brand"><div className="brand-icon"><Bug size={22} /></div><div><b>Bug Detective</b><small>AI DEBUG WORKSPACE</small></div><button className="mobile-close" onClick={() => setMobile(false)}><X /></button></div><div className="nav-label">WORKSPACE</div>{nav.map(([to, label, Icon]) => <Link key={to} to={to} onClick={() => setMobile(false)} className={`nav-link ${loc.pathname === to ? 'active' : ''}`}><Icon size={18} />{label}</Link>)}<div className="sidebar-bottom"><div className="secure"><ShieldCheck size={18} /><div><b>Workspace secured</b><small>JWT protected session</small></div></div><div className="profile"><div className="avatar">{user?.name?.slice(0, 1)?.toUpperCase() || 'U'}</div><div className="profile-copy"><b>{user?.name || 'Developer'}</b><small>{user?.role || 'DEVELOPER'}</small></div><button title="Logout" onClick={logout} className="icon-button"><LogOut size={17} /></button></div></div></aside><main className="main"><header className="topbar"><button className="mobile-menu icon-button" onClick={() => setMobile(true)}><Menu /></button><div><div className="eyebrow">ENGINEERING INTELLIGENCE</div><div className="top-title">AI Software Bug Detective</div></div><div className="top-right"><span className="online-dot" /> System workspace <div className="avatar small">{user?.name?.slice(0, 1)?.toUpperCase() || 'U'}</div></div></header><section className="content">{children}</section></main></div> }



function PageHead({ eyebrow, title, subtitle, action }) { return <div className="page-head"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div> }



function Button({ children, ...props }) { return <button className="btn" {...props}>{children}</button> }



function Error({ text }) { return text ? <div className="alert error">{text}</div> : null }



function Login() { const { login, token } = useAuth(); const nav = useNavigate(); const [register, setRegister] = useState(false); const [form, setForm] = useState({ name: '', email: '', password: '' }); const [error, setError] = useState(''); const [busy, setBusy] = useState(false); if (token) return <Navigate to="/" replace />; const change = e => setForm({ ...form, [e.target.name]: e.target.value }); const submit = async e => { e.preventDefault(); setError(''); setBusy(true); try { const { data } = await api.post(register ? '/auth/register' : '/auth/login', form); login(data); nav('/') } catch (err) { setError(messageOf(err)) } finally { setBusy(false) } }; return <div className="auth-page"><div className="auth-art"><div className="auth-logo"><Bug size={25} /></div><div className="eyebrow">AI-POWERED ENGINEERING</div><h1>Find the cause.<br /><span>Fix with confidence.</span></h1><p>Turn application errors into structured diagnosis, actionable fixes, and regression tests.</p><div className="art-panel"><div className="art-line"><span className="code-dot red" /><span className="code-dot yellow" /><span className="code-dot green" /><span className="muted">diagnostic_trace.log</span></div><code><i>01</i> ERROR: API request failed<br /><i>02</i> status_code = 500<br /><i>03</i> <span className="code-highlight">AI diagnosis ready</span><br /><i>04</i> root_cause → investigate backend</code></div></div><div className="auth-form-wrap"><form className="auth-form" onSubmit={submit}><div className="eyebrow">WELCOME TO YOUR WORKSPACE</div><h2>{register ? 'Create your account' : 'Sign in'}</h2><p>{register ? 'Start investigating issues with AI assistance.' : 'Continue to your engineering dashboard.'}</p><Error text={error} />{register && <label>Full name<input name="name" value={form.name} onChange={change} minLength="2" required placeholder="Your name" /></label>}<label>Email address<input type="email" name="email" value={form.email} onChange={change} required placeholder="you@company.com" /></label><label>Password<input type="password" name="password" value={form.password} onChange={change} minLength={register ? 8 : 1} required placeholder={register ? 'At least 8 characters' : 'Enter your password'} /></label><Button disabled={busy}>{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'} <span>→</span></Button><div className="switch-auth">{register ? 'Already have an account?' : 'New to Bug Detective?'} <button type="button" onClick={() => { setRegister(!register); setError('') }}>{register ? 'Sign in' : 'Create account'}</button></div><small className="disclaimer">AI output is a recommendation. Review changes before applying them.</small></form></div></div> }



function Dashboard() { const [data, setData] = useState(null); const [error, setError] = useState(''); useEffect(() => { api.get('/dashboard').then(r => setData(r.data)).catch(e => setError(messageOf(e))) }, []); return <><PageHead eyebrow="OVERVIEW / SYSTEM HEALTH" title="Your debugging command center" subtitle="A live view of project issues and investigation progress." action={<Link className="btn" to="/bugs/new"><Plus size={17} /> Report a bug</Link>} /><Error text={error} /><div className="stats-grid">{[['Tracked projects', data?.projects ?? '—', FolderKanban, 'Across your workspace'], ['Total bugs', data?.total_bugs ?? '—', Bug, 'Recorded issues'], ['Open issues', data?.open_bugs ?? '—', Activity, 'Require attention'], ['Critical bugs', data?.critical_bugs ?? '—', ShieldCheck, 'Highest severity']].map(([label, value, Icon, note]) => <div className="stat-card" key={label}><div className="stat-top"><span>{label}</span><span className="stat-icon"><Icon size={18} /></span></div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></div>)}</div><div className="section-grid"><div className="panel"><div className="panel-head"><div><h3>Recent bug activity</h3><p>Latest issues reported across projects</p></div><Link to="/bugs" className="text-link">View all →</Link></div>{!data ? <div className="empty">Loading workspace…</div> : data.recent_bugs.length === 0 ? <div className="empty"><div className="empty-icon"><Bug /></div><b>No bugs yet</b><p>Create a project, then report your first issue.</p><Link to="/projects" className="text-link">Go to projects →</Link></div> : <div className="table-wrap"><table><thead><tr><th>ISSUE</th><th>PROJECT</th><th>SEVERITY</th><th>STATUS</th></tr></thead><tbody>{data.recent_bugs.map(b => <tr key={b.id}><td><Link className="bug-link" to={`/bugs/${b.id}`}>BUG-{b.id} · {b.title}</Link></td><td>{b.project}</td><td><span className={`pill ${b.severity.toLowerCase()}`}>{b.severity}</span></td><td><span className="status">{b.status.replace('_', ' ')}</span></td></tr>)}</tbody></table></div>}</div><div className="panel ai-panel"><div className="ai-orb"><BrainCircuit size={27} /></div><div className="eyebrow">INVESTIGATION ENGINE</div><h3>From error to explanation</h3><p>Attach logs, provide reproduction steps, and run an AI-assisted analysis to get a probable root cause and suggested regression tests.</p><div className="ai-step"><span>01</span><div><b>Capture context</b><small>Logs, stack traces, expected result</small></div></div><div className="ai-step"><span>02</span><div><b>Analyze evidence</b><small>Probable cause and affected layer</small></div></div><div className="ai-step"><span>03</span><div><b>Validate the fix</b><small>Review generated test cases</small></div></div><Link to="/bugs/new" className="btn secondary full">Start an investigation</Link></div></div></> }



function Projects() { const [items, setItems] = useState([]), [error, setError] = useState(''), [show, setShow] = useState(false), [busy, setBusy] = useState(false); const [form, setForm] = useState({ name: '', description: '', technology: 'React, FastAPI', repository_url: '' }); const load = () => api.get('/projects').then(r => setItems(r.data)).catch(e => setError(messageOf(e))); useEffect(() => { load() }, []); const submit = async e => { e.preventDefault(); setBusy(true); setError(''); try { await api.post('/projects', form); setForm({ name: '', description: '', technology: 'React, FastAPI', repository_url: '' }); setShow(false); load() } catch (e) { setError(messageOf(e)) } finally { setBusy(false) } }; return <><PageHead eyebrow="WORKSPACE / PROJECTS" title="Projects" subtitle="Organize applications and track bugs in context." action={<Button onClick={() => setShow(!show)}><Plus size={17} /> New project</Button>} /><Error text={error} />{show && <form className="panel form-panel" onSubmit={submit}><h3>Create project</h3><div className="form-grid"><label>Project name<input required minLength="2" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Payments API" /></label><label>Technology stack<input value={form.technology} onChange={e => setForm({ ...form, technology: e.target.value })} placeholder="React, FastAPI, PostgreSQL" /></label><label className="span-2">Description<textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows="3" /></label><label className="span-2">Repository URL<input type="url" value={form.repository_url} onChange={e => setForm({ ...form, repository_url: e.target.value })} placeholder="https://github.com/..." /></label></div><div className="form-actions"><button type="button" className="btn secondary" onClick={() => setShow(false)}>Cancel</button><Button disabled={busy}>{busy ? 'Saving…' : 'Save project'}</Button></div></form>}<div className="project-grid">{items.map(p => <div className="project-card" key={p.id}><div className="project-card-top"><div className="project-icon"><FolderKanban /></div><span className="status">ACTIVE</span></div><h3>{p.name}</h3><p>{p.description || 'No description added yet.'}</p><div className="tech-tag">{p.technology || 'Technology not specified'}</div><div className="project-card-bottom"><span>Created {new Date(p.created_at).toLocaleDateString()}</span><Link to={`/bugs?project=${p.id}`} className="text-link">View bugs →</Link></div></div>)}{items.length === 0 && <div className="panel empty span-all"><div className="empty-icon"><FolderKanban /></div><b>No projects created</b><p>Create your first project to begin tracking bugs.</p><Button onClick={() => setShow(true)}><Plus size={16} /> Create project</Button></div>}</div></> }



function BugForm() { const [projects, setProjects] = useState([]), [error, setError] = useState(''), [busy, setBusy] = useState(false); const nav = useNavigate(); const [form, setForm] = useState({ title: '', project_id: '', description: '', error_message: '', reproduction_steps: '', expected_result: '', actual_result: '', module: 'General', environment: 'Development', severity: 'MEDIUM', status: 'OPEN' }); useEffect(() => { api.get('/projects').then(r => { setProjects(r.data); const id = new URLSearchParams(window.location.search).get('project'); if (id && r.data.some(p => p.id === Number(id))) setForm(f => ({ ...f, project_id: id })); else if (r.data[0]) setForm(f => ({ ...f, project_id: String(r.data[0].id) })) }).catch(e => setError(messageOf(e))) }, []); const change = e => setForm({ ...form, [e.target.name]: e.target.value }); const submit = async e => { e.preventDefault(); setBusy(true); setError(''); try { const { data } = await api.post('/bugs', { ...form, project_id: Number(form.project_id) }); nav(`/bugs/${data.id}`) } catch (e) { setError(messageOf(e)) } finally { setBusy(false) } }; return <><PageHead eyebrow="BUG MANAGEMENT / NEW ISSUE" title="Report a bug" subtitle="Capture enough evidence to make the investigation useful." /><Error text={error} />{projects.length === 0 ? <div className="panel empty"><b>Create a project first</b><p>Bugs must belong to a project.</p><Link to="/projects" className="btn">Open projects</Link></div> : <form className="panel form-panel" onSubmit={submit}><div className="form-grid"><label className="span-2">Bug title *<input name="title" value={form.title} onChange={change} required minLength="3" maxLength="220" placeholder="e.g. Login API returns 500 for valid user" /></label><label>Project *<select name="project_id" value={form.project_id} onChange={change} required>{projects.map(p => <option value={p.id} key={p.id}>{p.name}</option>)}</select></label><label>Severity<select name="severity" value={form.severity} onChange={change}>{['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(x => <option key={x}>{x}</option>)}</select></label><label>Module<input name="module" value={form.module} onChange={change} /></label><label>Environment<input name="environment" value={form.environment} onChange={change} /></label><label className="span-2">Description<textarea name="description" value={form.description} onChange={change} rows="3" placeholder="What happened? Include sanitized context." /></label><label className="span-2">Error message / stack trace<textarea name="error_message" value={form.error_message} onChange={change} rows="4" placeholder="Paste the relevant error. Remove secrets and personal data." /></label><label className="span-2">Steps to reproduce<textarea name="reproduction_steps" value={form.reproduction_steps} onChange={change} rows="3" /></label><label>Expected result<textarea name="expected_result" value={form.expected_result} onChange={change} rows="2" /></label><label>Actual result<textarea name="actual_result" value={form.actual_result} onChange={change} rows="2" /></label></div><div className="form-actions"><Link to="/bugs" className="btn secondary">Cancel</Link><Button disabled={busy}>{busy ? 'Creating…' : 'Create bug'}</Button></div></form>}</> }



function Bugs() { const [items, setItems] = useState([]), [projects, setProjects] = useState([]), [error, setError] = useState(''), [filter, setFilter] = useState('ALL'); const loc = useLocation(); useEffect(() => { api.get('/bugs', { params: new URLSearchParams(loc.search).get('project') ? { project_id: new URLSearchParams(loc.search).get('project') } : undefined }).then(r => setItems(r.data)).catch(e => setError(messageOf(e))); api.get('/projects').then(r => setProjects(r.data)).catch(() => { }) }, [loc.search]); const shown = filter === 'ALL' ? items : items.filter(b => b.status === filter); return <><PageHead eyebrow="BUG MANAGEMENT / TRACKER" title="Bug tracker" subtitle="Review issue status, severity, and investigation history." action={<Link className="btn" to="/bugs/new"><Plus size={17} /> Report a bug</Link>} /><Error text={error} /><div className="filter-row"><span>{shown.length} issues</span><select value={filter} onChange={e => setFilter(e.target.value)}><option value="ALL">All statuses</option>{['OPEN', 'ANALYZING', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'REOPENED'].map(x => <option key={x}>{x}</option>)}</select></div><div className="panel"><div className="table-wrap"><table><thead><tr><th>ISSUE</th><th>PROJECT</th><th>SEVERITY</th><th>STATUS</th><th>REPORTED</th></tr></thead><tbody>{shown.map(b => <tr key={b.id}><td><Link to={`/bugs/${b.id}`} className="bug-link">BUG-{b.id} · {b.title}</Link><div className="table-sub">{b.module} · {b.environment}</div></td><td>{projects.find(p => p.id === b.project_id)?.name || `Project #${b.project_id}`}</td><td><span className={`pill ${b.severity.toLowerCase()}`}>{b.severity}</span></td><td><span className="status">{b.status.replace('_', ' ')}</span></td><td>{new Date(b.created_at).toLocaleDateString()}</td></tr>)}</tbody></table>{shown.length === 0 && <div className="empty"><b>No matching bugs</b><p>Report an issue or choose a different status filter.</p></div>}</div></div></> }



function BugDetails() { const loc = useLocation(); const id = loc.pathname.split('/').pop(); const [bug, setBug] = useState(null), [analysis, setAnalysis] = useState([]), [attachments, setAttachments] = useState([]), [cases, setCases] = useState([]), [error, setError] = useState(''), [busy, setBusy] = useState(false), [file, setFile] = useState(null); const load = () => Promise.all([api.get(`/bugs/${id}`), api.get(`/bugs/${id}/analyses`), api.get(`/bugs/${id}/attachments`), api.get('/test-cases', { params: { bug_id: id } })]).then(([b, a, at, c]) => { setBug(b.data); setAnalysis(a.data); setAttachments(at.data); setCases(c.data) }).catch(e => setError(messageOf(e))); useEffect(() => { load() }, [id]); const upload = async e => { e.preventDefault(); if (!file) return; setBusy(true); setError(''); try { const body = new FormData(); body.append('file', file); await api.post(`/bugs/${id}/attachments`, body, { headers: { 'Content-Type': 'multipart/form-data' } }); setFile(null); await load() } catch (e) { setError(messageOf(e)) } finally { setBusy(false) } }; const run = async () => { setBusy(true); setError(''); try { await api.post(`/bugs/${id}/analyze`); await load() } catch (e) { setError(messageOf(e)) } finally { setBusy(false) } }; const toggle = async c => { try { await api.patch(`/test-cases/${c.id}`, { executed: !c.executed }); await load() } catch (e) { setError(messageOf(e)) } }; if (!bug && !error) return <div className="panel empty">Loading issue…</div>; if (!bug) return <Error text={error} />; const latest = analysis[0]; return <><PageHead eyebrow={`BUG MANAGEMENT / BUG-${bug.id}`} title={bug.title} subtitle={`${bug.module} · ${bug.environment} · Reported ${new Date(bug.created_at).toLocaleString()}`} action={<Link to="/bugs" className="btn secondary">← All bugs</Link>} /><Error text={error} /><div className="detail-layout"><div className="detail-main"><div className="panel"><div className="panel-head"><div><h3>Issue context</h3><p>Reproduction details and supplied evidence</p></div><span className={`pill ${bug.severity.toLowerCase()}`}>{bug.severity}</span></div><div className="context-block"><label>Description</label><p>{bug.description || 'No description provided.'}</p></div><div className="context-block"><label>Error message / stack trace</label><pre>{bug.error_message || 'No error message provided.'}</pre></div><div className="context-grid"><div><label>Expected result</label><p>{bug.expected_result || 'Not specified'}</p></div><div><label>Actual result</label><p>{bug.actual_result || 'Not specified'}</p></div></div><div className="context-block"><label>Steps to reproduce</label><p className="preline">{bug.reproduction_steps || 'Not specified'}</p></div></div><div className="panel"><div className="panel-head"><div><h3>Attachments</h3><p>Upload sanitized logs, code, or diagnostic files (10 MB maximum).</p></div></div><form className="upload-row" onSubmit={upload}><input type="file" accept=".log,.txt,.json,.pdf,.py,.js,.jsx,.sql,.png,.jpg,.jpeg" onChange={e => setFile(e.target.files?.[0] || null)} required /><Button disabled={busy || !file}>{busy ? 'Working…' : 'Upload file'}</Button></form>{attachments.map(a => <div className="attachment" key={a.id}><div className="file-icon">LOG</div><div><b>{a.original_name}</b><small>{(a.size_bytes / 1024).toFixed(1)} KB · {a.content_type}</small></div></div>)}{attachments.length === 0 && <p className="muted">No attachments uploaded yet.</p>}</div><div className="panel"><div className="panel-head"><div><h3>AI diagnosis</h3><p>Hypothesis based on the available context; verify before applying a fix.</p></div><Button onClick={run} disabled={busy}><BrainCircuit size={17} />{busy ? 'Analyzing…' : 'Run AI analysis'}</Button></div>{latest ? <><div className="diagnosis"><div className="diagnosis-head"><span className="ai-badge"><BrainCircuit size={16} /> ANALYSIS RESULT</span><span className="confidence">{Math.round(latest.confidence * 100)}% confidence</span></div><h4>Probable root cause</h4><p>{latest.root_cause}</p><div className="context-grid"><div><label>Affected component</label><p>{latest.affected_component}</p></div><div><label>Suggested severity</label><p><span className={`pill ${latest.severity.toLowerCase()}`}>{latest.severity}</span></p></div></div><h4>Possible causes</h4><p className="preline">{latest.possible_causes}</p><h4>Suggested fix</h4><pre>{latest.suggested_fix}</pre><h4>Recommended actions</h4><p className="preline">{latest.recommended_actions}</p><div className="provider-note">Provider: {latest.provider} · {new Date(latest.created_at).toLocaleString()}</div></div></> : <div className="empty compact"><div className="empty-icon"><BrainCircuit /></div><b>No diagnosis generated yet</b><p>Review the issue context and run an analysis.</p></div>}</div><div className="panel"><div className="panel-head"><div><h3>Generated test cases</h3><p>Mark each case after you execute it in your environment.</p></div><span className="status">{cases.filter(c => c.executed).length}/{cases.length} executed</span></div>{cases.length === 0 ? <div className="empty compact">Test cases appear after AI analysis.</div> : cases.map(c => <div className="test-case" key={c.id}><label className="test-check"><input type="checkbox" checked={c.executed} onChange={() => toggle(c)} /><span><b>{c.scenario}</b><small>{c.test_type} · {c.priority} PRIORITY</small></span></label><div className="test-case-details"><p><b>Input:</b> {c.input_data}</p><p><b>Expected:</b> {c.expected_result}</p></div></div>)}</div></div><aside className="detail-side"><div className="panel"><h3>Issue properties</h3><div className="property"><label>Status</label><span className="status">{bug.status.replace('_', ' ')}</span></div><div className="property"><label>Severity</label><span className={`pill ${bug.severity.toLowerCase()}`}>{bug.severity}</span></div><div className="property"><label>Module</label><b>{bug.module}</b></div><div className="property"><label>Environment</label><b>{bug.environment}</b></div><div className="property"><label>Project ID</label><b>#{bug.project_id}</b></div><div className="property"><label>Last updated</label><b>{new Date(bug.updated_at).toLocaleDateString()}</b></div></div><div className="panel tip-panel"><div className="tip-icon"><ShieldCheck /></div><h3>Safe debugging practice</h3><p>Never upload production credentials, access tokens, customer data, or private keys. AI suggestions must be reviewed and tested before use.</p></div></aside></div></> }



function Tests() { const [items, setItems] = useState([]), [error, setError] = useState(''); useEffect(() => { api.get('/test-cases').then(r => setItems(r.data)).catch(e => setError(messageOf(e))) }, []); return <><PageHead eyebrow="QUALITY / VALIDATION" title="Test cases" subtitle="Track the regression checks generated during bug investigations." /><Error text={error} /><div className="panel"><div className="table-wrap"><table><thead><tr><th>SCENARIO</th><th>BUG</th><th>TYPE</th><th>PRIORITY</th><th>EXECUTED</th></tr></thead><tbody>{items.map(c => <tr key={c.id}><td><Link className="bug-link" to={`/bugs/${c.bug_id}`}>{c.scenario}</Link><div className="table-sub">Expected: {c.expected_result}</div></td><td>BUG-{c.bug_id}</td><td>{c.test_type}</td><td><span className={`pill ${c.priority.toLowerCase()}`}>{c.priority}</span></td><td>{c.executed ? 'Yes' : 'Not yet'}</td></tr>)}</tbody></table>{items.length === 0 && <div className="empty"><div className="empty-icon"><ListChecks /></div><b>No test cases yet</b><p>Run AI analysis on a bug to generate test cases.</p><Link to="/bugs" className="text-link">Browse bugs →</Link></div>}</div></div></> }





function UploadProject() {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [generation, setGeneration] = useState(null);
  const [checks, setChecks] = useState(null);
  const [report, setReport] = useState(null);

  const chooseFile = (event) => {
    const selected = event.target.files?.[0] || null;
    setError('');
    setResult(null);
    setAnalysis(null);
    setGeneration(null);
    setChecks(null);
    setReport(null);

    if (selected && !selected.name.toLowerCase().endsWith('.zip')) {
      setFile(null);
      event.target.value = '';
      setError('Please select a ZIP file.');
      return;
    }
    if (selected && selected.size > 50 * 1024 * 1024) {
      setFile(null);
      event.target.value = '';
      setError('ZIP file must be 50 MB or smaller.');
      return;
    }
    setFile(selected);
  };

  const runAction = async (action, request, setter) => {
    if (!result?.upload_id) {
      setError('Upload a ZIP file first.');
      return;
    }
    setBusy(action);
    setError('');
    try {
      const response = await request(result.upload_id);
      setter(response.data);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy('');
    }
  };

  const upload = async (event) => {
    event.preventDefault();
    if (!file) {
      setError('Please choose a ZIP file first.');
      return;
    }
    setBusy('upload');
    setError('');
    setResult(null);
    setAnalysis(null);
    setGeneration(null);
    setChecks(null);
    setReport(null);
    try {
      const body = new FormData();
      body.append('file', file);
      const response = await api.post('/projects/upload-source', body);
      setResult(response.data);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy('');
    }
  };

  const analyzeSource = () =>
    runAction('analysis',
      (id) => api.post(`/projects/${encodeURIComponent(id)}/analyze-source`),
      setAnalysis);

  const generateCases = () =>
    runAction('generation',
      (id) => api.post(`/projects/${encodeURIComponent(id)}/generate-test-cases`),
      setGeneration);

  const runChecks = async () => {
    await runAction('checks',
      (id) => api.post(`/projects/${encodeURIComponent(id)}/run-tests`),
      setChecks);
  };

  const loadReport = async () => {
    await runAction('report',
      (id) => api.get(`/projects/${encodeURIComponent(id)}/test-report`),
      setReport);
  };
    const downloadExcel = async () => {
    if (!result?.upload_id) {
      setError('Upload a ZIP file first.');
      return;
    }

    setBusy('excel');
    setError('');

    try {
      const blob = await downloadProjectTestReportExcel(result.upload_id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = url;
      link.download = `bug-detective-report-${result.upload_id}.xlsx`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy('');
    }
  };

  const count = (obj, keys) => {
    for (const key of keys) {
      if (typeof obj?.[key] === 'number') return obj[key];
    }
    return 0;
  };

  return <>
    <PageHead
      eyebrow="AUTOMATED TESTING / SOURCE PROJECT"
      title="Upload & inspect project"
      subtitle="Upload a ZIP, inspect source files, generate test ideas, run safe static checks, and view the report."
    />
    <Error text={error} />
    <div className="panel" style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 22 }}>
        <div className="project-icon"><UploadCloud size={25} /></div>
        <div>
          <h3 style={{ margin: '0 0 5px' }}>Project source</h3>
          <p className="muted" style={{ margin: 0 }}>ZIP only · Maximum 50 MB</p>
        </div>
      </div>
      <form onSubmit={upload}>
        <label htmlFor="project-zip" style={{ display: 'block', marginBottom: 8 }}>Choose project ZIP file</label>
        <input
          id="project-zip"
          type="file"
          accept=".zip,application/zip,application/x-zip-compressed"
          onChange={chooseFile}
          style={{ display: 'block', width: '100%', padding: 14, border: '1px dashed var(--border, #cbd5e1)', borderRadius: 10, marginBottom: 16 }}
        />
        {file && <div className="attachment" style={{ marginBottom: 16 }}>
          <div className="file-icon"><FileArchive size={18} /></div>
          <div><b>{file.name}</b><small>{(file.size / 1024).toFixed(1)} KB</small></div>
        </div>}
        <Button disabled={Boolean(busy) || !file}>
          <UploadCloud size={17} /> {busy === 'upload' ? 'Uploading and validating…' : 'Upload Project ZIP'}
        </Button>
      </form>

      {result && <>
        <div className="panel" style={{ marginTop: 22, border: '1px solid #86efac', background: 'rgba(34,197,94,0.06)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <CheckCircle2 color="#16a34a" size={23} />
            <div><h3 style={{ margin: 0 }}>Upload successful</h3><small className="muted">ZIP validated and stored by the backend.</small></div>
          </div>
          <div className="property"><label>File name</label><b>{result.filename}</b></div>
          <div className="property"><label>Upload status</label><span className="status">{result.status}</span></div>
          <div className="property"><label>Files detected</label><b>{result.file_count}</b></div>
          <div className="property"><label>File size</label><b>{(Number(result.size_bytes || 0) / 1024).toFixed(1)} KB</b></div>
          <div className="property"><label>Upload ID</label><code style={{ overflowWrap: 'anywhere' }}>{result.upload_id}</code></div>
        </div>

        <div className="panel" style={{ marginTop: 18 }}>
          <h3>Analysis & test workflow</h3>
          <p className="muted">Run each stage in order. These endpoints inspect files and perform static checks; they do not execute arbitrary uploaded project code.</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <Button type="button" disabled={Boolean(busy)} onClick={analyzeSource}>
              {busy === 'analysis' ? 'Analyzing…' : '1. Analyze source'}
            </Button>
            <Button type="button" disabled={Boolean(busy) || !analysis} onClick={generateCases}>
              {busy === 'generation' ? 'Generating…' : '2. Generate test cases'}
            </Button>
            <Button type="button" disabled={Boolean(busy) || !analysis} onClick={runChecks}>
              {busy === 'checks' ? 'Running checks…' : '3. Run static checks'}
            </Button>
            <Button type="button" disabled={Boolean(busy) || !checks} onClick={loadReport}>
              {busy === 'report' ? 'Loading report…' : '4. View test report'}
            </Button>
            <Button
              type="button"
              disabled={Boolean(busy) || !checks}
              onClick={downloadExcel}
            >
              {busy === 'excel' ? 'Downloading Excel…' : '5. Download Excel Report'}
            </Button>
          </div>
        </div>

        {analysis && <div className="panel" style={{ marginTop: 18 }}>
          <h3>Source analysis</h3>
          <div className="stats-grid">
            <div className="stat-card"><div className="stat-top">Total files</div><div className="stat-value">{analysis.total_files ?? '—'}</div></div>
            <div className="stat-card"><div className="stat-top">Source files</div><div className="stat-value">{analysis.source_file_count ?? '—'}</div></div>
          </div>
          <div className="property"><label>Project kind</label><b>{analysis.project_kind || analysis.project_type || 'Detected project'}</b></div>
          <div className="property"><label>Languages</label><b>{analysis.languages ? Object.entries(analysis.languages).map(([name, n]) => `${name} (${n})`).join(', ') : 'Not returned'}</b></div>
          <div className="property"><label>Frameworks</label><b>{Array.isArray(analysis.frameworks_detected) ? analysis.frameworks_detected.join(', ') : 'Not detected'}</b></div>
          <div className="property"><label>Dependency files</label><span>{Array.isArray(analysis.dependency_files) ? analysis.dependency_files.join(', ') : 'None listed'}</span></div>
        </div>}

        {generation && <div className="panel" style={{ marginTop: 18 }}>
          <h3>Generated test cases ({count(generation, ['test_case_count', 'count']) || generation.test_cases?.length || 0})</h3>
          <p className="muted">Generated cases are proposals until they are implemented and executed by a supported test runner.</p>
          {(generation.test_cases || []).map((test, index) => <div className="test-case" key={test.case_number || index}>
            <b>{test.case_number ? `Case ${test.case_number}: ` : ''}{test.scenario || 'Test scenario'}</b>
            <div className="test-case-details">
              <p><b>Input:</b> {test.input_data || 'Not specified'}</p>
              <p><b>Expected:</b> {test.expected_result || 'Not specified'}</p>
              <p><b>Priority / type:</b> {test.priority || '—'} / {test.test_type || '—'}</p>
              <p><b>Status:</b> {test.execution_status || 'NOT_RUN'}</p>
            </div>
          </div>)}
          {(!generation.test_cases || generation.test_cases.length === 0) && <p className="muted">The API did not return test case details.</p>}
          {generation.provider && <div className="provider-note">Provider: {generation.provider}</div>}
        </div>}

        {checks && <div className="panel" style={{ marginTop: 18 }}>
          <h3>Static check results</h3>
          <div className="stats-grid">
            <div className="stat-card"><div className="stat-top">Total checks</div><div className="stat-value">{count(checks, ['total_checks', 'total'])}</div></div>
            <div className="stat-card"><div className="stat-top">Passed</div><div className="stat-value">{count(checks, ['passed', 'passed_checks'])}</div></div>
            <div className="stat-card"><div className="stat-top">Failed</div><div className="stat-value">{count(checks, ['failed', 'failed_checks_count'])}</div></div>
            <div className="stat-card"><div className="stat-top">Errors</div><div className="stat-value">{count(checks, ['errors', 'error_count'])}</div></div>
          </div>
          <p className="muted">{checks.note || 'Static checks do not prove the application is bug-free and are not the same as executing generated test cases.'}</p>
          {(checks.all_results || checks.results || []).map((item, index) => <div className="attachment" key={`${item.check || 'check'}-${index}`}>
            <div className="file-icon">{item.status || 'CHECK'}</div>
            <div><b>{item.check || item.name || `Check ${index + 1}`}</b><small>{item.details || item.message || ''}</small></div>
          </div>)}
        </div>}

        {report && <div className="panel" style={{ marginTop: 18 }}>
          <h3>Test report</h3>
          <div className="property"><label>Overall status</label><b>{report.overall_status || report.status || 'Report ready'}</b></div>
          <div className="property"><label>Report type</label><b>{report.report_type || 'Static checks'}</b></div>
          {report.summary && <div className="stats-grid">
            <div className="stat-card"><div className="stat-top">Total checks</div><div className="stat-value">{count(report.summary, ['total_checks', 'total'])}</div></div>
            <div className="stat-card"><div className="stat-top">Passed</div><div className="stat-value">{count(report.summary, ['passed'])}</div></div>
            <div className="stat-card"><div className="stat-top">Failed</div><div className="stat-value">{count(report.summary, ['failed'])}</div></div>
            <div className="stat-card"><div className="stat-top">Errors</div><div className="stat-value">{count(report.summary, ['errors'])}</div></div>
          </div>}
          {(report.all_results || []).map((item, index) => <div className="attachment" key={`${item.check || 'report'}-${index}`}>
            <div className="file-icon">{item.status || 'CHECK'}</div>
            <div><b>{item.check || `Check ${index + 1}`}</b><small>{item.details || ''}</small></div>
          </div>)}
          <p className="muted">This report currently summarizes static source checks. Full application-level PASS/FAIL results require a configured isolated test runner.</p>
        </div>}
      </>}

      <div className="tip-panel" style={{ marginTop: 22 }}>
        <h3>Before uploading</h3>
        <p>Remove .env files, passwords, API keys, access tokens, private keys, customer data, and unnecessary dependency folders such as node_modules or .venv.</p>
      </div>
    </div>
  </>;
}

function AppRoutes() { return <Routes><Route path="/login" element={<Login />} /><Route path="/*" element={<Protected><Shell><Routes><Route path="/" element={<Dashboard />} /><Route path="/projects" element={<Projects />} /><Route path="/upload" element={<UploadProject />} /><Route path="/bugs" element={<Bugs />} /><Route path="/bugs/new" element={<BugForm />} /><Route path="/bugs/:id" element={<BugDetails />} /><Route path="/tests" element={<Tests />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></Shell></Protected>} /></Routes> }



export default function App() { return <AuthProvider><AppRoutes /></AuthProvider> }
