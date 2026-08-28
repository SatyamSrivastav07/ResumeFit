function FeatureCard({ number, title, description }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
      <span className="mb-5 grid size-10 place-items-center rounded-full bg-brand-50 text-sm font-bold text-brand-700">
        {number}
      </span>
      <h2 className="text-lg font-bold text-ink">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
    </article>
  )
}

export default FeatureCard

