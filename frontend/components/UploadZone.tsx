"use client"
import { useRef, useState } from "react"
import { Upload, FileText } from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
  onFile: (file: File) => void
  loading?: boolean
}

export function UploadZone({ onFile, loading }: Props) {
  const [drag, setDrag] = useState(false)
  const ref = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDrag(false)
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
  }

  return (
    <div
      onClick={() => !loading && ref.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      className={cn(
        "border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all",
        drag ? "border-indigo-400 bg-indigo-50" : "border-slate-200 hover:border-slate-300 hover:bg-slate-50",
        loading && "opacity-50 cursor-not-allowed"
      )}
    >
      <input
        ref={ref}
        type="file"
        accept=".pdf,.pptx"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f) }}
      />
      <Upload className="mx-auto mb-3 text-slate-400" size={32} />
      <p className="text-sm font-medium text-slate-700">Drop a pitch deck here</p>
      <p className="text-xs text-slate-400 mt-1">PDF or PPTX · up to 50 MB</p>
    </div>
  )
}
