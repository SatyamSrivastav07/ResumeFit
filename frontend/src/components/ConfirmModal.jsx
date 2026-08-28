function ConfirmModal({ description, onCancel, onConfirm, title }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 id="confirm-title" className="text-xl font-black text-ink">{title}</h2>
        <p className="mt-3 leading-7 text-slate-600">{description}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold" onClick={onCancel} type="button">Cancel</button>
          <button className="rounded-xl bg-red-700 px-4 py-2 text-sm font-bold text-white" onClick={onConfirm} type="button">Delete</button>
        </div>
      </div>
    </div>
  )
}
export default ConfirmModal
