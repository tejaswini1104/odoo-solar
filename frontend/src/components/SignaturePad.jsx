import React, { useEffect, useRef, useState } from 'react';

// A small drawing area for the homeowner's signature. Works with a finger, a pen or a mouse.
// onChange receives a PNG data URL after each stroke, or null when the pad is cleared.
export default function SignaturePad({ onChange, disabled = false }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const [hasInk, setHasInk] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#0f172a';
  }, []);

  const point = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * canvas.width,
      y: ((event.clientY - rect.top) / rect.height) * canvas.height,
    };
  };

  const start = (event) => {
    if (disabled) return;
    event.preventDefault();
    canvasRef.current.setPointerCapture(event.pointerId);
    drawing.current = true;
    const ctx = canvasRef.current.getContext('2d');
    const { x, y } = point(event);
    ctx.beginPath();
    ctx.moveTo(x, y);
    // A tap leaves a dot
    ctx.lineTo(x + 0.01, y + 0.01);
    ctx.stroke();
  };

  const move = (event) => {
    if (!drawing.current || disabled) return;
    event.preventDefault();
    const ctx = canvasRef.current.getContext('2d');
    const { x, y } = point(event);
    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const end = () => {
    if (!drawing.current) return;
    drawing.current = false;
    setHasInk(true);
    onChange?.(canvasRef.current.toDataURL('image/png'));
  };

  const clear = () => {
    const canvas = canvasRef.current;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    setHasInk(false);
    onChange?.(null);
  };

  return (
    <div>
      <canvas
        ref={canvasRef}
        width={600}
        height={220}
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerCancel={end}
        style={{ touchAction: 'none' }}
        className={`w-full h-36 rounded-lg border-2 border-dashed ${disabled ? 'border-slate-200 bg-slate-100' : 'border-slate-300 bg-white'} cursor-crosshair`}
      />
      <div className="flex items-center justify-between mt-1.5">
        <span className="text-[11px] text-slate-500">{hasInk ? 'Signature drawn' : 'Sign inside the box'}</span>
        <button
          type="button"
          onClick={clear}
          disabled={disabled || !hasInk}
          className="text-[11px] font-semibold text-slate-600 hover:text-slate-900 disabled:opacity-40"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
