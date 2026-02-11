"use client";

import { Separator } from "react-resizable-panels";

interface ResizeHandleProps {
  onDragging?: (isDragging: boolean) => void;
}

export function ResizeHandle({ onDragging }: ResizeHandleProps) {
  return (
    <Separator
      className="group relative w-2 flex items-center justify-center data-[resize-handle-active]:bg-blue-500/10"
      onPointerDown={() => onDragging?.(true)}
      onPointerUp={() => onDragging?.(false)}
    >
      {/* Visible line */}
      <div className="w-px h-full bg-zinc-800 group-hover:w-[3px] group-hover:bg-blue-500/50 group-data-[resize-handle-active]:w-[3px] group-data-[resize-handle-active]:bg-blue-500 transition-all duration-150 rounded-full" />
    </Separator>
  );
}
