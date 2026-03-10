import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import GeneratePage from './pages/GeneratePage'
import BenchmarkPage from './pages/BenchmarkPage'
import RepoDetailPage from './pages/RepoDetailPage'

function Nav() {
  const base = 'px-4 py-2 text-sm font-medium rounded-md transition-colors'
  const active = 'bg-indigo-600 text-white'
  const inactive = 'text-slate-400 hover:text-white hover:bg-slate-700'

  return (
    <nav className="flex items-center gap-2 px-6 py-3 bg-slate-900 border-b border-slate-800">
      <span className="text-white font-semibold mr-6 text-sm tracking-wide">Repo Onboarding Agent</span>
      <NavLink to="/" end className={({ isActive }) => `${base} ${isActive ? active : inactive}`}>
        Generate
      </NavLink>
      <NavLink to="/benchmark" className={({ isActive }) => `${base} ${isActive ? active : inactive}`}>
        Benchmark
      </NavLink>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <Nav />
        <Routes>
          <Route path="/" element={<GeneratePage />} />
          <Route path="/benchmark" element={<BenchmarkPage />} />
          <Route path="/benchmark/:owner/:repo" element={<RepoDetailPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
