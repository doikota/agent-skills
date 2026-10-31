import { useEffect, useMemo, useRef, useState } from 'react'
import { X } from 'lucide-react'

type Task = { id: string; text: string; done: boolean; createdAt: number; sample?: boolean }
type Filter = 'all' | 'active' | 'done'

const KEY = 'aosa-tasks.v1'
const now = Date.now()
const SAMPLES: Task[] = [
  { id: 's1', text: '朝いちばんに今週の目標を3つ書き出す', done: true, createdAt: now - 86400000 * 2, sample: true },
  { id: 's2', text: '企画書のたたき台をチームに共有する', done: false, createdAt: now - 86400000, sample: true },
  { id: 's3', text: 'まだ試していない方法をひとつ選んで挑む', done: false, createdAt: now - 3600000, sample: true },
]

const isTask = (v: unknown): v is Task => {
  if (typeof v !== 'object' || v === null) return false
  const t = v as Record<string, unknown>
  return typeof t.id === 'string' && typeof t.text === 'string' && typeof t.done === 'boolean' && typeof t.createdAt === 'number'
}

/* 保存データが壊れている・形式が違う場合はサンプルに戻す */
function load(): Task[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const data: unknown = JSON.parse(raw)
      if (Array.isArray(data)) return data.filter(isTask)
    }
  } catch { /* storage unavailable or invalid JSON */ }
  return SAMPLES
}
function save(tasks: Task[]) {
  try { localStorage.setItem(KEY, JSON.stringify(tasks)) } catch { /* ignore */ }
}
const fmt = (t: number) => {
  const d = new Date(t)
  return `${d.getMonth() + 1}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function Streaks() {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const c = ref.current!
    const ctx = c.getContext('2d')!
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let raf = 0
    const lines = Array.from({ length: 34 }, (_, i) => ({
      y: 0.05 + (i / 34) * 0.85,
      amp: 0.04 + Math.random() * 0.08,
      freq: 1.2 + Math.random() * 1.4,
      speed: 0.15 + Math.random() * 0.35,
      width: 1 + Math.random() * 7,
      alpha: 0.08 + Math.random() * 0.28,
      phase: Math.random() * Math.PI * 2,
    }))
    const draw = (t: number) => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = c.clientWidth, h = c.clientHeight
      if (c.width !== w * dpr || c.height !== h * dpr) { c.width = w * dpr; c.height = h * dpr }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)
      ctx.globalCompositeOperation = 'lighter'
      for (const l of lines) {
        const g = ctx.createLinearGradient(0, 0, w, 0)
        g.addColorStop(0, 'rgba(60,140,255,0)')
        g.addColorStop(0.35, `rgba(110,180,255,${l.alpha})`)
        g.addColorStop(0.7, `rgba(190,225,255,${l.alpha * 0.9})`)
        g.addColorStop(1, 'rgba(60,140,255,0)')
        ctx.strokeStyle = g
        ctx.lineWidth = l.width
        ctx.filter = l.width > 5 ? 'blur(3px)' : 'none'
        ctx.beginPath()
        for (let x = -20; x <= w + 20; x += 16) {
          const p = x / w
          const y = (l.y + Math.sin(p * l.freq * Math.PI + l.phase + t * 0.001 * l.speed) * l.amp - p * 0.12) * h
          x === -20 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        }
        ctx.stroke()
      }
      ctx.filter = 'none'
      if (!reduce) raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [])
  return <canvas ref={ref} aria-hidden="true" />
}

/* 正面を見据える人物のシルエット（ショートボブ・淡いブルーのシャツ） */
function Figure() {
  return (
    <svg className="figure" viewBox="0 0 200 260" aria-hidden="true">
      <defs>
        <radialGradient id="face" cx="50%" cy="42%" r="60%">
          <stop offset="0" stopColor="#f6efee" />
          <stop offset="1" stopColor="#c9d4f2" />
        </radialGradient>
        <linearGradient id="shirt" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#a9c8f5" />
          <stop offset="1" stopColor="#6f9be0" />
        </linearGradient>
        <linearGradient id="hair" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#141a3a" />
          <stop offset="1" stopColor="#070a1f" />
        </linearGradient>
      </defs>
      <path d="M8 260 C14 214 52 196 84 190 L116 190 C148 196 186 214 192 260 Z" fill="url(#shirt)" />
      <path d="M86 160 L114 160 L118 196 Q100 206 82 196 Z" fill="#dcc9cb" />
      <path d="M100 20 C58 20 44 52 44 92 C44 130 50 156 54 170 L70 170 C64 140 64 112 72 88 L128 88 C136 112 136 140 130 170 L146 170 C150 156 156 130 156 92 C156 52 142 20 100 20 Z" fill="url(#hair)" />
      <ellipse cx="100" cy="108" rx="34" ry="46" fill="url(#face)" />
      <path d="M66 96 C70 62 86 44 100 42 C114 44 130 62 134 96 C122 78 112 66 100 62 C90 70 80 80 66 96 Z" fill="url(#hair)" />
      <ellipse cx="86" cy="108" rx="5" ry="3.2" fill="#1a1f3d" />
      <ellipse cx="114" cy="108" rx="5" ry="3.2" fill="#1a1f3d" />
      <path d="M92 134 Q100 138 108 134 Q100 141 92 134 Z" fill="#c9767a" />
    </svg>
  )
}

export default function App() {
  const [tasks, setTasks] = useState<Task[]>(load)
  const [text, setText] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  /* 5 秒以内に続けて削除したものは、まとめて元に戻せる（削除順に積む） */
  const [removed, setRemoved] = useState<{ task: Task; index: number }[]>([])
  const timer = useRef<number>()

  useEffect(() => save(tasks), [tasks])

  const doneCount = tasks.filter((t) => t.done).length
  const activeCount = tasks.length - doneCount
  const visible = useMemo(
    () => tasks.filter((t) => (filter === 'all' ? true : filter === 'done' ? t.done : !t.done)),
    [tasks, filter],
  )

  const add = (e: React.FormEvent) => {
    e.preventDefault()
    const v = text.trim()
    if (!v) return
    setTasks((ts) => [{ id: crypto.randomUUID?.() ?? String(Math.random()), text: v, done: false, createdAt: Date.now() }, ...ts])
    setText('')
    if (filter === 'done') setFilter('all')
  }
  const toggle = (id: string) => setTasks((ts) => ts.map((t) => (t.id === id ? { ...t, done: !t.done } : t)))
  const remove = (id: string) => {
    const index = tasks.findIndex((t) => t.id === id)
    if (index < 0) return
    setRemoved((r) => [...r, { task: tasks[index], index }])
    setTasks((ts) => ts.filter((t) => t.id !== id))
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setRemoved([]), 5000)
  }
  const undo = () => {
    if (!removed.length) return
    window.clearTimeout(timer.current)
    // 後に削除したものから順に、削除時の位置へ戻す
    setTasks((ts) => {
      const n = [...ts]
      for (const r of [...removed].reverse()) n.splice(Math.min(r.index, n.length), 0, r.task)
      return n
    })
    setRemoved([])
  }
  useEffect(() => () => window.clearTimeout(timer.current), [])

  const pct = tasks.length ? Math.round((doneCount / tasks.length) * 100) : 0
  const filters: { key: Filter; label: string; n: number }[] = [
    { key: 'all', label: 'すべて', n: tasks.length },
    { key: 'active', label: '挑戦中', n: activeCount },
    { key: 'done', label: '実った', n: doneCount },
  ]

  return (
    <>
      <header className="hero">
        <Streaks />
        <div className="hero-inner">
          <div>
            <h1 className="tagline">青さで、<br />挑む。</h1>
            <p className="sub">ともに挑む。ともに実る。</p>
          </div>
          <Figure />
        </div>
      </header>

      <main className="wrap">
        <section className="panel" aria-labelledby="ttl">
          <div className="panel-head">
            <h2 id="ttl" className="panel-title">今日の挑戦</h2>
            <div className="stats" aria-live="polite">
              <span>挑戦中 <b>{activeCount}</b></span>
              <span>実った <b>{doneCount}</b></span>
              <span>達成率 <b>{pct}%</b></span>
            </div>
          </div>
          <div className="meter" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="達成率">
            <span style={{ width: `${pct}%` }} />
          </div>

          <form className="add" onSubmit={add}>
            <label htmlFor="new-task" className="sr-only">新しいタスク</label>
            <input id="new-task" value={text} onChange={(e) => setText(e.target.value)} placeholder="次に挑むことを書く" autoComplete="off" maxLength={120} />
            <button className="btn-add" type="submit" disabled={!text.trim()}>追加</button>
          </form>

          <div className="filters" role="group" aria-label="表示の切り替え">
            {filters.map((f) => (
              <button key={f.key} type="button" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>
                {f.label}<span className="n">{f.n}</span>
              </button>
            ))}
          </div>

          {visible.length ? (
            <ul className="list">
              {visible.map((t) => (
                <li key={t.id} className={`item${t.done ? ' done' : ''}`}>
                  <input
                    type="checkbox"
                    className="chk"
                    id={`c-${t.id}`}
                    checked={t.done}
                    onChange={() => toggle(t.id)}
                    aria-label={t.done ? '未完了に戻す' : '完了にする'}
                  />
                  <label htmlFor={`c-${t.id}`} className="text cursor-pointer">
                    {t.text}
                    {t.sample && <span className="tag">サンプル</span>}
                    <span className="meta">{fmt(t.createdAt)} 追加</span>
                  </label>
                  <button type="button" className="del" onClick={() => remove(t.id)} aria-label={`「${t.text}」を削除`}>
                    <X size={18} />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty">
              {filter === 'done' ? 'まだ実ったタスクはありません。ひとつ完了にしてみましょう。' : filter === 'active' ? '挑戦中のタスクはありません。上の欄から次の挑戦を追加できます。' : 'タスクはまだありません。上の欄に書いて「追加」を押してください。'}
            </p>
          )}
        </section>
      </main>

      {removed.length > 0 && (
        <div className="toast" role="status">
          <span>{removed.length > 1 ? `${removed.length}件削除しました` : '削除しました'}</span>
          <button type="button" onClick={undo}>元に戻す</button>
        </div>
      )}
    </>
  )
}
